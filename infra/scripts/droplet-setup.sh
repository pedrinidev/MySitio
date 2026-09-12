#!/usr/bin/env bash
#
# Preparación de un Droplet de DigitalOcean recién creado (Ubuntu 24.04)
# para alojar pedrinidev.com.
#
#   ssh root@<IP>
#   curl -fsSL https://raw.githubusercontent.com/pedrinidev/mysite/main/infra/scripts/droplet-setup.sh -o setup.sh
#   less setup.sh          # ← leelo antes de ejecutarlo. Siempre.
#   bash setup.sh
#
# Es IDEMPOTENTE: se puede volver a ejecutar sin romper nada.
#
# ⚠️  MODIFICA la configuración de SSH, el cortafuegos y la memoria virtual.
#     Pide confirmación antes de cada cambio que pueda dejarte fuera.

set -euo pipefail

# ─────────────────────────── Parámetros ────────────────────────────
DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/srv/mysite}"
SWAP_SIZE="${SWAP_SIZE:-2G}"
SSH_PORT="${SSH_PORT:-22}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${BLUE}→${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

confirm() {
    read -rp "$(echo -e "${YELLOW}?${NC} $1 [s/N] ")" answer
    [[ "$answer" =~ ^[sSyY]$ ]]
}

[ "$(id -u)" -eq 0 ] || fail "Ejecutá este script como root."

echo
echo "════════════════════════════════════════════════════════"
echo "  Preparación del droplet — pedrinidev.com"
echo "════════════════════════════════════════════════════════"
echo "  Usuario de despliegue : $DEPLOY_USER"
echo "  Directorio            : $APP_DIR"
echo "  Swap                  : $SWAP_SIZE"
echo "  RAM detectada         : $(free -m | awk '/^Mem:/{print $2}') MB"
echo "════════════════════════════════════════════════════════"
echo

# ───────────────────── 1. Sistema al día ───────────────────────────
log "Actualizando paquetes del sistema…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    ca-certificates curl gnupg lsb-release \
    ufw fail2ban unattended-upgrades sqlite3 git htop
ok "Sistema actualizado"

# ───────────────────── 2. Swap ─────────────────────────────────────
# En 512 MB de RAM el swap no es opcional: es el colchón que impide que el
# OOM killer se lleve a Gunicorn durante un pico. No es memoria extra —es
# órdenes de magnitud más lento— pero convierte una caída en una lentitud.
if swapon --show | grep -q '/swapfile'; then
    ok "Swap ya configurado ($(free -h | awk '/^Swap:/{print $2}'))"
else
    log "Creando $SWAP_SIZE de swap…"
    fallocate -l "$SWAP_SIZE" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    ok "Swap activo"
fi

# swappiness=10: usar swap solo cuando de verdad haga falta. El valor por
# defecto (60) empuja páginas al disco de forma preventiva y en un disco de
# red eso se nota en cada petición.
cat > /etc/sysctl.d/99-mysite.conf <<'SYSCTL'
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=1024
net.ipv4.tcp_fin_timeout=20
SYSCTL
sysctl -p /etc/sysctl.d/99-mysite.conf >/dev/null
ok "Parámetros del kernel ajustados (swappiness=10)"

# ───────────────────── 3. Usuario de despliegue ────────────────────
if id "$DEPLOY_USER" &>/dev/null; then
    ok "El usuario $DEPLOY_USER ya existe"
else
    log "Creando el usuario $DEPLOY_USER…"
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
    usermod -aG sudo "$DEPLOY_USER"
    ok "Usuario creado"
fi

# Se copian las claves de root para no quedarse fuera del servidor.
mkdir -p "/home/$DEPLOY_USER/.ssh"
if [ -f /root/.ssh/authorized_keys ]; then
    cat /root/.ssh/authorized_keys >> "/home/$DEPLOY_USER/.ssh/authorized_keys"
    sort -u "/home/$DEPLOY_USER/.ssh/authorized_keys" -o "/home/$DEPLOY_USER/.ssh/authorized_keys"
fi
chmod 700 "/home/$DEPLOY_USER/.ssh"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys" 2>/dev/null || true
chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
ok "Claves SSH copiadas a $DEPLOY_USER"

# ───────────────────── 4. Docker ───────────────────────────────────
if command -v docker &>/dev/null; then
    ok "Docker ya instalado ($(docker --version))"
else
    log "Instalando Docker…"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    ok "Docker instalado"
fi

usermod -aG docker "$DEPLOY_USER"

# ⚠️ Rotación de logs de Docker.
#
# Esta es LA causa más común de caída en droplets pequeños: sin rotación,
# los logs JSON crecen sin límite hasta llenar los 10 GB de disco, y entonces
# no arranca nada. Diez líneas de configuración que ahorran una noche
# depurando un servidor que «dejó de funcionar sin motivo».
cat > /etc/docker/daemon.json <<'DOCKERD'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
DOCKERD
systemctl restart docker
systemctl enable docker >/dev/null 2>&1
ok "Rotación de logs de Docker configurada (10 MB × 3)"

# ───────────────────── 5. Cortafuegos ──────────────────────────────
log "Configurando UFW…"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow "$SSH_PORT"/tcp comment 'SSH' >/dev/null
ufw allow 80/tcp comment 'HTTP' >/dev/null
ufw allow 443/tcp comment 'HTTPS' >/dev/null
ufw --force enable >/dev/null
ok "Cortafuegos activo (solo $SSH_PORT, 80 y 443)"

# ───────────────────── 6. fail2ban ─────────────────────────────────
cat > /etc/fail2ban/jail.local <<'F2B'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
F2B
systemctl enable fail2ban >/dev/null 2>&1
systemctl restart fail2ban
ok "fail2ban activo"

# ───────────────────── 7. Actualizaciones automáticas ──────────────
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'AUTO'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
AUTO
ok "Actualizaciones de seguridad automáticas activadas"

# ───────────────────── 8. Directorio de la aplicación ──────────────
mkdir -p "$APP_DIR"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"
ok "Directorio $APP_DIR listo"

# ───────────────────── 9. Tareas programadas ───────────────────────
cat > /etc/cron.d/mysite <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Muestra de métricas cada 5 minutos (también purga las de más de 24 h).
*/5 * * * * $DEPLOY_USER cd $APP_DIR && docker compose -f compose.prod.yml exec -T api python manage.py snapshot_metrics >/dev/null 2>&1

# Renovación del certificado: dos veces al día, como recomienda Let's Encrypt.
# Solo actúa si faltan menos de 30 días para la caducidad.
17 3,15 * * * root cd $APP_DIR && docker compose -f compose.prod.yml run --rm certbot renew --quiet && docker compose -f compose.prod.yml exec -T web nginx -s reload

# Respaldo diario de SQLite a las 3:30.
#
# La salida va a un registro y NO a /dev/null. Tenerlo silenciado costó
# caro: el guion fallaba cada noche con «sqlite3: not found» y la carpeta
# de respaldos llevaba días vacía sin que nada lo delatara. Un respaldo que
# falla en silencio es peor que no tener respaldo, porque encima da
# confianza. Una línea al día no llena ningún disco.
30 3 * * * $DEPLOY_USER cd $APP_DIR && ./backup.sh >> $APP_DIR/backup.log 2>&1

# Limpieza semanal de imágenes huérfanas (el disco son solo 10 GB).
0 4 * * 0 root docker image prune -af --filter "until=168h" >/dev/null 2>&1
CRON
chmod 644 /etc/cron.d/mysite
ok "Tareas programadas instaladas"

# ───────────────────── 10. Endurecimiento de SSH ───────────────────
echo
warn "El siguiente paso deshabilita el acceso SSH por contraseña y como root."
warn "ANTES de aceptar, abrí OTRA terminal y comprobá que esto funciona:"
echo
echo "      ssh $DEPLOY_USER@$(curl -fsS -4 icanhazip.com 2>/dev/null || echo '<IP>')"
echo
warn "Si esa conexión falla y aceptás igual, quedás fuera del servidor."
echo

if confirm "¿Confirmás que podés entrar como $DEPLOY_USER con tu clave?"; then
    cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'SSHD'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
SSHD
    sshd -t && systemctl reload ssh
    ok "SSH endurecido: solo clave pública, sin acceso root"
else
    warn "SSH sin endurecer. Ejecutá el script otra vez cuando lo hayas comprobado."
fi

# ───────────────────── Resumen ─────────────────────────────────────
echo
echo "════════════════════════════════════════════════════════"
echo -e "  ${GREEN}Droplet preparado${NC}"
echo "════════════════════════════════════════════════════════"
free -h | sed 's/^/  /'
echo
df -h / | sed 's/^/  /'
echo
echo "  Siguientes pasos:"
echo "   1. Apuntá el DNS de pedrinidev.com a $(curl -fsS -4 icanhazip.com 2>/dev/null || echo 'esta IP')"
echo "   2. Copiá compose.prod.yml, .env y backup.sh a $APP_DIR"
echo "   3. Emití el certificado:  ./init-ssl.sh"
echo "   4. Cargá los secretos en GitHub y hacé push a main"
echo
echo "  Documentación completa: docs/deployment.md"
echo "════════════════════════════════════════════════════════"
