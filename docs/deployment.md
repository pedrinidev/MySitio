# Despliegue — de cero a pedrinidev.com

> Última actualización: 2026-09-10
> Destino: Droplet de DigitalOcean, 512 MB RAM · 1 vCPU · 10 GB SSD · 4 USD/mes

Esta guía va en orden. Cada paso asume que el anterior terminó bien.

---

## Antes de empezar

| Necesitás | Dónde |
|---|---|
| Cuenta de DigitalOcean | digitalocean.com |
| Dominio `pedrinidev.com` | Spaceship (ya comprado) |
| Buzón de Zoho Mail | zoho.com/mail — plan gratuito (solo para **recibir**) |
| Bot de Telegram | @BotFather — gratis, para el aviso del formulario |
| Repositorio en GitHub | `pedrinidev/MySitio` |
| Clave SSH | `ssh-keygen -t ed25519 -C "pedrinidevs@gmail.com"` |

---

## 1. Crear el droplet

En DigitalOcean → **Create → Droplet**:

- **Imagen:** Ubuntu 24.04 LTS
- **Plan:** Basic → Regular → **$4/mes** (512 MB / 1 vCPU / 10 GB)
- **Región:** New York o San Francisco *(las más cercanas a Bolivia con buena latencia)*
- **Autenticación:** **SSH Key** — nunca contraseña
- **Hostname:** `pedrinidev`

Anotá la IP pública.

> **Sobre el tamaño:** 512 MB alcanza porque el droplet solo sirve archivos y
> ejecuta Django. Todo el trabajo pesado —compilar Astro, construir imágenes—
> ocurre en GitHub Actions. Si algún día el droplet empieza a compilar, se cae.

---

## 2. Preparar el servidor

```bash
ssh root@<IP>

curl -fsSL https://raw.githubusercontent.com/pedrinidev/MySitio/main/infra/scripts/droplet-setup.sh -o setup.sh
less setup.sh          # leelo antes de ejecutarlo
bash setup.sh
```

El script deja listo:

- Usuario `deploy` sin privilegios, con tus claves SSH
- **2 GB de swap** con `swappiness=10` — el colchón que impide que el OOM
  killer se lleve a Gunicorn durante un pico
- Docker + Compose
- **Rotación de logs de Docker** (10 MB × 3) — sin esto, los logs llenan los
  10 GB de disco en semanas; es la causa más común de caída en droplets pequeños
- UFW (solo 22, 80, 443), fail2ban, actualizaciones de seguridad automáticas
- Tareas de cron: métricas cada 5 min, renovación TLS, respaldo diario, limpieza semanal

> ⚠️ Al final pide confirmación para deshabilitar el acceso por contraseña.
> **Antes de aceptar**, abrí otra terminal y comprobá que `ssh deploy@<IP>`
> funciona. Si aceptás sin comprobarlo y la clave no está bien copiada, quedás
> fuera del servidor y hay que recrearlo.

---

## 3. Apuntar el dominio

En el panel DNS de **Spaceship**:

| Tipo | Nombre | Valor | TTL |
|---|---|---|---|
| A | `@` | `<IP del droplet>` | 300 |
| A | `www` | `<IP del droplet>` | 300 |

Comprobá la propagación antes de seguir — Certbot fallará si el DNS todavía
no resuelve:

```bash
dig +short pedrinidev.com
```

Hasta que ese comando devuelva la IP del droplet, **no continúes**.

---

## 4. Configurar el aviso del formulario

> **DigitalOcean bloquea SMTP.** Los puertos 25, 465, 587 y 2525 no
> responden desde un droplet; el 443 sí. Se comprobó desde el servidor. No
> es configurable: el bloqueo está en la red del proveedor, no en la
> máquina. Por eso el aviso sale por una API HTTPS y no por SMTP.
>
> Zoho sigue siendo útil para **recibir** correo en `@pedrinidev.com` — los
> registros MX no se ven afectados. Lo que cambia es por dónde **sale** el
> aviso del formulario.

Los canales se eligen con `NOTIFY_CHANNELS` en el `.env`, separados por
comas. Hay dos, y el código de cada uno vive en
`apps/api/core/notifications.py`.

**Se pueden activar los dos a la vez** (`NOTIFY_CHANNELS=telegram,email`), y
es lo más robusto: el aviso sale por ambos y un canal caído no deja al otro
sin enviar. El mensaje se da por entregado con que **uno** lo consiga; solo
si fallan todos queda marcado como no entregado en el Admin. El fallo de
cada canal se registra por separado, porque un canal roto mientras el otro
funciona no se nota de ninguna otra forma.

### 4.1 Telegram (canal por defecto)

Es el que menos pide: no hace falta dominio verificado, ni registros DNS,
ni cuenta de correo transaccional. Y el aviso llega al teléfono en lugar de
a una bandeja que se revisa cada tres días, que para una oferta de pasantía
es la diferencia que importa.

1. En Telegram, escribile a **@BotFather** y mandale `/newbot`. Te pide un
   nombre y un usuario que termine en `bot`.
2. Copiá el token que devuelve — tiene la forma `123456789:AAE...`.
3. **Escribile cualquier cosa a tu bot nuevo.** Sin esto no existe la
   conversación y el paso siguiente sale vacío.
4. Abrí `https://api.telegram.org/bot<TOKEN>/getUpdates` en el navegador y
   copiá el número de `"chat":{"id":...}`.
5. En el `.env` del servidor:

   ```ini
   NOTIFY_CHANNELS=telegram
   TELEGRAM_BOT_TOKEN=<el token de BotFather>
   TELEGRAM_CHAT_ID=<el id numérico>
   ```

El token es una credencial: quien lo tenga manda mensajes como el bot. Va
en el `.env` con permisos `600`, nunca en el repositorio. El código lo
oculta también en los registros de error, porque `requests` incluye la URL
—y el token va dentro de la URL— en el texto de sus excepciones.

### 4.2 Resend (alternativa por correo)

Si preferís que el aviso llegue como correo desde `contacto@pedrinidev.com`:

1. Creá una cuenta en [resend.com](https://resend.com) — 3.000 correos al
   mes gratis, sin tarjeta.
2. Añadí el dominio `pedrinidev.com` y poné los registros DNS que te
   indique (DKIM y un TXT de verificación) en Spaceship.
3. Generá una clave en *API Keys* y poné en el `.env`:

   ```ini
   NOTIFY_CHANNELS=email
   RESEND_API_KEY=<la clave>
   ```

Sin dominio verificado, Resend solo deja enviar desde su dominio de pruebas
`onboarding@resend.dev`, y solo **a la dirección con la que te registraste**.
Para este sitio eso alcanza —el aviso siempre va a la misma cuenta— así que
se puede saltar el paso 2 y configurar `DEFAULT_FROM_EMAIL=onboarding@resend.dev`.
Verificar el dominio es lo que permite que el aviso salga desde
`contacto@pedrinidev.com`, que se ve mejor si algún día lo reenviás.

### 4.2 Zoho Mail, para recibir

1. En Zoho Mail, añadí `pedrinidev.com` y verificá la propiedad con el
   registro TXT que te indiquen.
2. Añadí los registros MX de Zoho en Spaceship.
3. Creá el buzón `contacto@pedrinidev.com`.
4. **Generá una contraseña de aplicación** en *Security → App Passwords*.
   No uses tu contraseña principal: si se filtra el `.env` del servidor,
   una contraseña de aplicación se revoca sola, la principal compromete la cuenta.

---

## 5. Colocar los archivos en el droplet

```bash
ssh deploy@<IP>
mkdir -p /srv/mysite && cd /srv/mysite
```

Desde tu máquina:

```bash
scp infra/compose.prod.yml infra/scripts/init-ssl.sh infra/scripts/backup.sh \
    deploy@<IP>:/srv/mysite/
```

Creá el `.env` **en el servidor** (nunca lo subas al repositorio):

```bash
ssh deploy@<IP>
cd /srv/mysite
cat > .env <<'EOF'
DJANGO_SECRET_KEY=<openssl rand -hex 32>
DJANGO_ALLOWED_HOSTS=pedrinidev.com,www.pedrinidev.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://pedrinidev.com,https://www.pedrinidev.com
DJANGO_ADMIN_URL=panel-<algo-no-obvio>/
CORS_ALLOWED_ORIGINS=https://pedrinidev.com

DATABASE_PATH=/data/db.sqlite3
MEDIA_ROOT=/data/media
STATIC_ROOT=/data/static

IP_HASH_SALT=<openssl rand -hex 32>
GAME_TOKEN_SECRET=<openssl rand -hex 32>

# Aviso del formulario de contacto. Ver la sección 4.
NOTIFY_CHANNELS=telegram
TELEGRAM_BOT_TOKEN=<el token que da @BotFather>
TELEGRAM_CHAT_ID=<el id numérico de getUpdates>

DEFAULT_FROM_EMAIL=contacto@pedrinidev.com
CONTACT_TO_EMAIL=pedrinidevs@gmail.com

# El mismo valor que el secreto BUILD_API_TOKEN de GitHub. Exime al build
# del límite de peticiones: sin él, generar 20 páginas dispara el 429 y el
# despliegue falla entero.
BUILD_API_TOKEN=<openssl rand -hex 32>

# Reconstrucción automática al publicar desde el Admin. Empezá en 0: se
# activa cuando tengas el token, y mientras tanto Django arranca igual.
REBUILD_WEBHOOK_ENABLED=0
# GITHUB_DISPATCH_TOKEN=<token con permiso contents:write, solo este repo>
# GITHUB_REPOSITORY=pedrinidev/MySitio

PUBLIC_SITE_URL=https://pedrinidev.com
EOF
chmod 600 .env
```

`DJANGO_SETTINGS_MODULE`, `HOST_PROC_PATH` y `HOST_ROOT_PATH` **no** van aquí:
los define `compose.prod.yml`, porque describen cómo se monta el contenedor
y no cambian de una instalación a otra.

Django se niega a arrancar en producción si falta alguna de estas cuatro:
`DJANGO_SECRET_KEY` (de menos de 50 caracteres no vale), `DJANGO_ADMIN_URL`
(no puede quedarse en `admin/`), las credenciales del canal de avisos que
esté elegido en `NOTIFY_CHANNELS`, y el par del webhook cuando está activado. Son fallos de arranque a propósito: una configuración
a medias que levanta es peor que una que se niega.

**Los tres secretos deben ser distintos entre sí.** Reutilizar la misma clave
para firmar tokens y para hashear IPs anula el aislamiento entre ambos usos.

---

## 6. Cargar los secretos

### 6.1 Workflows

Los workflows viven en `.github/workflows/`, la única ruta donde GitHub
Actions los busca. No hay nada que mover.

`deploy.yml` empieza comprobando si existe el secreto `DROPLET_HOST`. Si no
existe, los jobs de despliegue quedan **omitidos** en lugar de fallidos: el
repositorio no acumula cruces rojas por un servidor que aún no está, y el
despliegue se activa solo en cuanto se carguen los secretos de abajo.

### 6.2 Secretos

En el repositorio de GitHub → **Settings → Secrets and variables → Actions**:

| Secreto | Valor |
|---|---|
| `DROPLET_HOST` | IP del droplet |
| `DROPLET_USER` | `deploy` |
| `DROPLET_SSH_KEY` | Contenido de tu clave **privada** (`~/.ssh/id_ed25519`) |
| `BUILD_API_TOKEN` | El **mismo valor** que pusiste en el `.env` del droplet |

> La clave privada en un secreto de GitHub es la práctica habitual para
> desplegar por SSH, pero conviene que sea una clave **dedicada al despliegue**,
> no tu clave personal. Generala aparte y añadí solo su pública al droplet.

> **Sobre `BUILD_API_TOKEN`:** prerenderizar el sitio son ~22 peticiones a la
> API en pocos segundos desde una sola IP —justo el patrón que el límite
> anónimo (60/min) existe para frenar. Sin este token, el propio despliegue
> se autobloquea con un 429. Viaja como *secreto de BuildKit*, no como
> build-arg, para que no quede grabado en el historial de la imagen: con el
> repositorio público, cualquiera podría leerlo desde GHCR.

---

## 7. Primer despliegue

El orden importa y no es negociable: **la API antes que el sitio**. Astro
consulta la API durante el build; si no existe todavía, el build falla o
publica un sitio vacío.

### 7.1 Levantar la API a mano (solo esta vez)

```bash
ssh deploy@<IP> && cd /srv/mysite

# Autenticarse en GHCR para descargar la imagen
echo <TOKEN_GITHUB> | docker login ghcr.io -u pedrinidev --password-stdin

export API_IMAGE=ghcr.io/pedrinidev/mysitio-api:latest
docker compose -f compose.prod.yml up -d api
docker compose -f compose.prod.yml exec -T api python manage.py migrate --noinput
docker compose -f compose.prod.yml exec -T api python manage.py createcachetable
docker compose -f compose.prod.yml exec -T api python manage.py collectstatic --noinput
docker compose -f compose.prod.yml exec -it api python manage.py createsuperuser
docker compose -f compose.prod.yml exec -T api python manage.py seed_content
```

> La imagen de la API tiene que existir en GHCR. Si es la primera vez,
> lanzá el workflow **Deploy** a mano desde la pestaña Actions; fallará en
> `build-web` (todavía no hay API en pie) pero dejará la imagen publicada.

### 7.2 Emitir el certificado TLS

```bash
chmod +x init-ssl.sh

# Primero en modo prueba, para no gastar la cuota de Let's Encrypt
STAGING=1 ./init-ssl.sh

# Si sale bien, el certificado real
./init-ssl.sh
```

Let's Encrypt permite **5 certificados por dominio y semana**. Agotar esa
cuota con intentos fallidos deja el dominio bloqueado siete días — de ahí que
el primer intento vaya siempre en `STAGING=1`.

### 7.3 Despliegue completo

```bash
git push origin main
```

A partir de aquí el pipeline hace todo: CI → imagen de la API → desplegar API
→ imagen del sitio (consultando la API en vivo) → desplegar sitio.

---

## 8. Comprobación posterior

```bash
curl -I https://pedrinidev.com                 # 200, con HSTS y CSP
curl -I http://pedrinidev.com                  # 301 a https
curl -s https://pedrinidev.com/api/v1/health/  # {"status":"ok"}
curl -so /dev/null -w "%{http_code}" https://pedrinidev.com/es/no-existe   # 404
```

Y en el navegador:

- [ ] `https://pedrinidev.com` redirige a `/es/`
- [ ] El selector cambia a `/en/` y el contenido está en inglés
- [ ] El dashboard muestra RAM y CPU **del host**, no del contenedor
      *(si dice ~8 GB de RAM, el montaje de `/proc` no está funcionando)*
- [ ] El formulario de contacto hace llegar el aviso por el canal configurado
- [ ] Los juegos guardan puntuación y el ranking se actualiza
- [ ] El admin responde en la ruta no obvia que pusiste en `DJANGO_ADMIN_URL`
- [ ] SSL Labs da **A o A+**: https://www.ssllabs.com/ssltest/analyze.html?d=pedrinidev.com

---

## 9. Operación diaria

```bash
# Estado
docker compose -f compose.prod.yml ps
docker stats --no-stream

# Logs
docker compose -f compose.prod.yml logs -f --tail=100 api

# Memoria (lo que más importa en 512 MB)
free -h

# Respaldo manual
./backup.sh
```

### Publicar contenido

Entrá al admin, escribí, guardá. Django dispara la reconstrucción del sitio
y en ~2 minutos está publicado. **No hace falta tocar el servidor.**

### Revertir un despliegue

```bash
export API_IMAGE=ghcr.io/pedrinidev/mysitio-api:<sha-anterior>
export WEB_IMAGE=ghcr.io/pedrinidev/mysitio-web:<sha-anterior>
docker compose -f compose.prod.yml up -d
```

Los SHA están en la pestaña Actions y en Packages. Por eso cada imagen se
etiqueta con el SHA además de con `latest`.

### Comprobar que los respaldos existen

```bash
docker run --rm -v mysite_api_data:/data alpine ls -la /data/backups/
tail -5 /srv/mysite/backup.log
```

**Hacelo de vez en cuando.** El respaldo corre a las 3:30 por cron y durante
los primeros días falló **todas las noches en silencio**: el guion llamaba al
binario `sqlite3`, que está instalado en el host pero no dentro del
contenedor de la API, y el cron mandaba la salida a `/dev/null`. La carpeta
de respaldos llevaba días vacía sin que nada lo delatara. Ahora el guion usa
el módulo `sqlite3` de Python —la misma API de respaldo en línea— y el cron
escribe en `backup.log`.

Un respaldo que falla en silencio es peor que no tener respaldo: encima da
confianza.

### Restaurar la base de datos

```bash
docker compose -f compose.prod.yml stop api
docker compose -f compose.prod.yml run --rm --entrypoint sh api -c \
  "gunzip -c /data/backups/db-2026-09-10.sqlite3.gz > /data/db.sqlite3"
docker compose -f compose.prod.yml start api
```

Antes de confiar en un respaldo, restauralo **a un archivo aparte** y
comprobalo — sin tocar la base en uso:

```bash
docker compose -f compose.prod.yml exec -T api python -c "
import gzip, shutil, sqlite3
with gzip.open('/data/backups/db-2026-09-12.sqlite3.gz') as f:
    shutil.copyfileobj(f, open('/tmp/p.sqlite3','wb'))
con = sqlite3.connect('/tmp/p.sqlite3')
print(con.execute('PRAGMA integrity_check').fetchone()[0])
print(con.execute('SELECT COUNT(*) FROM projects_project').fetchone()[0], 'proyectos')
"
```

### Sacar los respaldos del droplet

Los respaldos viven en el **mismo servidor** que protegen. Eso cubre un error
humano o una migración mal aplicada; **no cubre perder el droplet**. Para eso
hay que sacarlos fuera, y esto se ejecuta desde tu equipo:

```bash
rsync -az -e "ssh -i ~/.ssh/pedrinidev" \
  deploy@pedrinidev.com:/var/lib/docker/volumes/mysite_api_data/_data/backups/ \
  ~/Respaldos/pedrinidev/
```

---

## 10. Cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| **502 Bad Gateway** | El contenedor `api` está caído | `docker compose logs api`; casi siempre es OOM o una migración fallida |
| **La RAM del dashboard es de 8 GB** | El montaje de `/proc` no llegó | Comprobá los `volumes` de `api` en `compose.prod.yml` |
| **El sitio no se actualiza al publicar** | Falta `GITHUB_DISPATCH_TOKEN` o le sobra/falta permiso | Mirá los logs de `api`; buscá `mysite.webhooks` |
| **El aviso no llega** | `TELEGRAM_CHAT_ID` equivocado, o no le escribiste al bot antes de sacarlo | Los mensajes **siguen guardados** en el admin: no se pierde ninguno. `docker compose logs api \| grep Telegram` da el motivo exacto |
| **La carpeta de respaldos está vacía** | El cron falla en silencio (`>/dev/null`) | `tail /srv/mysite/backup.log`; si no existe, ejecutá `./backup.sh` a mano para ver el error real |
| **El certificado no renueva** | El reto ACME se está redirigiendo a HTTPS | Verificá que `location /.well-known/acme-challenge/` sigue en `site.conf` |
| **Disco lleno** | Logs o imágenes viejas | `docker system df` y `docker image prune -af` |
| **`database is locked`** | WAL no se aplicó | `docker compose exec api python -c "from django.db import connection; connection.cursor().execute('PRAGMA journal_mode')"` |
| **El sitio se ve pero sin contenido** | El build de Astro no alcanzó la API | Revisá el job `build-web`: debe fallar, no publicar vacío |
| **`build-web` falla con HTTP 429** | Falta `BUILD_API_TOKEN`, o no coincide con el del droplet | Deben ser idénticos en el secreto de GitHub y en el `.env` del servidor |
| **Un cambio en `.env` no surte efecto** | Se usó `docker compose restart` | `restart` reutiliza la configuración anterior; hace falta `up -d` para releer `env_file` |

### El servidor no responde en absoluto

```bash
ssh deploy@<IP>
free -h                  # ¿se comió la RAM?
df -h                    # ¿se llenó el disco?
docker compose -f /srv/mysite/compose.prod.yml ps
sudo dmesg | grep -i "killed process"    # ¿actuó el OOM killer?
```

Si el OOM killer mató a Gunicorn de forma recurrente, no lo maquilles
reiniciando: revisá si `--workers 2` sigue siendo apropiado o si algo nuevo
está consumiendo memoria que antes no existía.
