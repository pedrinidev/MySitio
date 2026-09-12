# Registro de decisiones de arquitectura (ADR)

> Trazabilidad del sistema. Toda decisión estructural se anota aquí con su fecha, su motivo y su costo.
> Una decisión sin costo anotado es una decisión mal entendida.

---

### ADR-001 · Astro estático con islas React, en lugar de SSR — 2026-09-10 · **aceptada**

**Contexto.** El destino tiene 512 MB de RAM. Un proceso Node para SSR consume 80–120 MB adicionales
sobre un presupuesto que ya está al 75 % de ocupación.

**Decisión.** Astro compila a HTML estático en GitHub Actions, consumiendo la API de Django en tiempo de
build. Solo las partes verdaderamente dinámicas se hidratan como islas React.

**Consecuencias.** ✅ Cero RAM adicional · ✅ SEO completo · ✅ el sitio sobrevive a la caída de Django.
❌ Publicar contenido cuesta ~2 minutos de rebuild · ❌ aparece una dependencia de orden en el primer
despliegue: la API debe estar en pie antes de construir el frontend.

---

### ADR-002 · Los builds ocurren en CI, nunca en el droplet — 2026-09-10 · **aceptada**

**Contexto.** `docker build` de Astro tiene picos de 400–800 MB de RAM y los layers acumulados llenan
un disco de 10 GB en semanas.

**Decisión.** GitHub Actions construye y publica las imágenes en GHCR. El droplet solo ejecuta
`docker compose pull && up -d`.

**Consecuencias.** ✅ El droplet nunca queda sin memoria durante un despliegue · ✅ rollback inmediato
cambiando de tag · ✅ el pipeline es en sí mismo parte del portafolio.
❌ Depende de la disponibilidad de GHCR · ❌ requiere gestionar secretos de registro.

---

### ADR-003 · Campos por idioma en lugar de django-modeltranslation — 2026-09-10 · **aceptada**

**Decisión.** Cada modelo declara `campo_es` y `campo_en` explícitamente. Un mixin de serializador aplana
según `?lang=`.

**Consecuencias.** ✅ Sin dependencias ni magia · ✅ migraciones legibles · ✅ Admin comprensible.
❌ Añadir un tercer idioma (aymara, que sería un diferenciador real dado que es lengua nativa del autor)
exige una migración con columnas nuevas por cada modelo. **Costo aceptado conscientemente.**

---

### ADR-004 · SQLite en modo WAL en lugar de PostgreSQL — 2026-09-10 · **aceptada**

**Decisión.** SQLite con WAL, sobre volumen Docker persistente y respaldo diario mediante `.backup`.

**Consecuencias.** ✅ ~120 MB de RAM ahorrados · ✅ latencia menor (sin red ni proceso servidor) ·
✅ respaldo = un archivo. ❌ Sin escrituras concurrentes reales · ❌ migrar a Postgres si algún día hay
tráfico serio · ❌ el volumen es un punto único de fallo, mitigado con el respaldo diario.

---

### ADR-005 · Three.js excluido del MVP — 2026-09-10 · **aceptada**

**Decisión.** No se incluye en la primera versión.

**Motivo.** ~150 KB comprimidos compiten directamente con el objetivo de LCP < 1,5 s en móvil, que es
el escenario principal de un reclutador. Se reevalúa en M11, y solo con importación diferida y
activación bajo demanda.

---

### ADR-006 · Búsqueda con `icontains` antes que FTS5 — 2026-09-10 · **aceptada**

**Decisión.** Búsqueda simple en el MVP; FTS5 planificado para M11.

**Motivo.** Con menos de 200 posts, `icontains` responde en milisegundos. Construir un índice de texto
completo antes de tener contenido que lo justifique es optimización prematura.

---

### ADR-007 · `mobile_flow.md` documenta la web móvil, no una app nativa — 2026-09-10 · **aceptada**

**Motivo.** Las reglas del proyecto exigen el documento; el sistema no tiene app nativa. Se documenta la
ausencia y se cubre lo que sí aplica, en lugar de inventar capas MVVM sin sujeto. Ver `mobile_flow.md`.

---

### ADR-008 · Montaje de `/proc` del host en modo lectura — 2026-09-10 · **aceptada con riesgo**

**Decisión.** El contenedor `api` monta `/proc`, `/sys` y `/` del host en modo solo lectura para que
`psutil` mida el droplet real y no el contenedor.

**Riesgo asumido.** Expone la lista de procesos del host al contenedor. Aceptable en un droplet de un
solo inquilino y de un solo propietario. **No sería aceptable** en infraestructura compartida o
multi-tenant. Queda registrado para que la decisión no se herede sin revisar.

---

### ADR-009 · Los wheels se montan, no se copian, en la imagen de la API — 2026-09-10 · **aceptada**

**Contexto.** La primera versión hacía `COPY --from=builder /wheels /wheels`
seguido de `pip install && rm -rf /wheels`. La imagen medía **287 MB**.

**Problema.** El `COPY` graba los wheels en su propia capa de forma permanente.
El `rm` posterior solo los oculta en las capas siguientes: no recupera un byte.

**Decisión.** Consumirlos con `RUN --mount=type=bind,from=builder`, que los
expone durante la ejecución del comando sin dejar rastro en ninguna capa.

**Resultado medido.** 287 MB → **226 MB**. La imagen del sitio queda en 77 MB.

---

### ADR-010 · Las cabeceras de seguridad viven en un archivo incluido — 2026-09-10 · **aceptada**

**Contexto.** Estaban declaradas en el bloque `server` de Nginx. Una prueba
end-to-end reveló que **ninguna llegaba al navegador**.

**Causa.** En Nginx, `add_header` se hereda del nivel superior *solo si el
nivel actual no define ninguna*. El `location /` añadía su propio
`Cache-Control` y, con eso, descartaba silenciosamente HSTS, CSP,
`X-Frame-Options` y el resto.

**Decisión.** Extraerlas a `security_headers.conf` e incluirlo explícitamente
en el `server` **y en cada location** que añada cabeceras propias.

**Por qué importa.** Es un fallo que no da ningún error: la configuración
carga, el sitio funciona y se publica sin protecciones. Solo se detecta
mirando las cabeceras de una respuesta real — razón por la que la
comprobación quedó incorporada a la lista de verificación posterior al
despliegue.

---

### ADR-011 · Un 404 debe responder 404 — 2026-09-10 · **aceptada**

**Contexto.** `try_files $uri $uri/index.html $uri.html /404.html;` servía la
página de error **con código 200**.

**Consecuencia.** Google indexaría cada URL rota como una página válida, y
cualquier monitorización externa vería el sitio sano mientras sirve errores.

**Decisión.** `try_files ... =404;` combinado con `error_page 404 /404.html;`,
que entrega la página propia con el código correcto.

---

### ADR-012 · React, no Preact, pese al coste — 2026-09-10 · **aceptada con reserva**

**Contexto.** El runtime de React son **65,5 KB comprimidos**. Preact con
`compat` haría lo mismo en ~11 KB: unos 55 KB de ahorro en toda página con una
isla.

**Decisión.** Se mantiene React, que es lo que especifica el encargo.

**Mitigación.** Ninguna isla es bloqueante: la home entrega **1,8 KB** de
JavaScript inicial y todo lo demás (GSAP 44,8 KB, React 65,5 KB) se carga de
forma diferida o al entrar en pantalla. El LCP no se ve afectado.

**Cuándo revisarlo.** Si una auditoría en un móvil de gama media sobre 4G real
no alcanza el objetivo de LCP < 1,5 s, el cambio a Preact es la primera
palanca: sustituir la integración en `astro.config.mjs` y añadir los alias de
tipos. Los componentes no cambian.

---

### ADR-013 · El build se exime del límite de peticiones — 2026-09-10 · **aceptada**

**Contexto.** Al construir el sitio contra la API real, el build falló con
**HTTP 429**. Prerenderizar 22 páginas en dos idiomas son ~22 peticiones en
pocos segundos desde una sola IP: exactamente el patrón que el límite anónimo
de 60/min existe para frenar.

**Gravedad.** No era un problema local. En GitHub Actions el runner sale por
una única IP y habría fallado igual, **rompiendo todos los despliegues**.
Ninguna prueba unitaria lo detectaba porque ninguna ejercitaba ese patrón:
solo apareció al construir de verdad contra la API de verdad.

**Decisión.** Dos medidas complementarias:

1. **Memoria de peticiones durante el build** (`apps/web/src/lib/api.ts`).
   El despachador de rutas y cada página pedían los mismos listados por
   separado. Deduplicar bajó de **54 a 22 peticiones**.
2. **Cabecera `X-Build-Token`** que exime del límite, comparada en tiempo
   constante con `secrets.compare_digest`. Viaja como *secreto de BuildKit*,
   nunca como build-arg: un build-arg queda en `docker history` y, con el
   repositorio público, sería legible desde GHCR.

**Salvaguarda.** Con `BUILD_API_TOKEN` vacío —el valor por defecto— la
exención queda desactivada por completo. Una configuración incompleta no
puede convertirse en una puerta abierta.

**Verificado.** 70 peticiones con token válido → 70 × 200. Con token
incorrecto → 429 a partir de la 61.ª. Cubierto por
`core/tests/test_throttling.py`.

---

### ADR-014 · Las lecturas y las escrituras usan cachés de throttling distintas — 2026-09-10 · **aceptada**

**Contexto.** Con toda la limitación apoyada en `DatabaseCache`, medir las
consultas reveló que **cada petición pagaba ~5 consultas a SQLite solo para
llevar la cuenta**. El endpoint de métricas —que no toca la base de datos—
gastaba 6 consultas por llamada, y lo consulta cada visitante cada 15 s.

**Decisión.**

- **Lecturas → `LocMemCache`.** El límite de 60/min existe para frenar
  rastreadores, no para contar con precisión. Con 2 workers el límite efectivo
  es 120/min, que sigue cumpliendo su función.
- **Escrituras → `DatabaseCache`.** Aquí la precisión sí importa: «3 mensajes
  por hora» que en realidad son 6 —uno por worker— deja de ser un límite. Son
  endpoints de volumen bajísimo, así que el coste no se nota.

**Resultado medido.** Métricas 6 → **0** consultas. Listados 9 → **3**.
Perfil 18 → **5**. Peor caso de toda la API: 5 consultas.

---

### ADR-015 · Las páginas de sección emiten h1, no h2 — 2026-09-10 · **aceptada**

**Contexto.** Una auditoría sobre el HTML generado encontró **10 páginas sin
ningún `<h1>`**: el componente `SectionHeading` emitía siempre `h2`, y las
páginas de sección lo usaban como titular principal.

**Impacto.** Quien navega con lector de pantalla pierde el punto de entrada al
documento, y Google se queda sin la señal más clara del tema de la página.

**Decisión.** `SectionHeading` acepta `level`, con `2` por defecto (el uso más
frecuente) y `1` explícito en las cinco páginas de sección.

**Lección de método.** El defecto no se veía revisando el código —cada
componente parecía correcto por separado— sino auditando el HTML final. Las
comprobaciones sobre la salida real encuentran cosas que la lectura del
código no.

---

### ADR-016 · El aviso del formulario sale por Telegram, no por correo — 2026-09-11 · **aceptada**

**Contexto.** El formulario de contacto es la única vía por la que llega una
oferta, y su aviso falló dos veces seguidas por motivos distintos:

1. **SMTP por Zoho.** DigitalOcean bloquea los puertos 25, 465, 587 y 2525 en
   sus droplets. Se comprobó desde el servidor: el 443 abierto, los de correo
   muertos. No es configurable — el bloqueo está en la red del proveedor.
2. **API de Resend.** Esquiva el bloqueo porque viaja por el 443, pero exige
   verificar el dominio con registros DKIM antes de poder enviar desde
   `contacto@pedrinidev.com`.

**Decisión.** El canal por defecto pasa a ser la API de bots de Telegram, y la
elección se hace con `NOTIFY_CHANNELS` — en plural, porque **se pueden activar
varios a la vez**. Razones, en orden:

- **No pide nada.** Ni dominio verificado, ni registros DNS, ni cuenta de
  correo transaccional. Un token de @BotFather y un id de conversación.
- **Avisa donde se mira.** El aviso llega al teléfono, no a una bandeja que se
  revisa cada tres días. Para una oferta de pasantía, esa diferencia es el
  motivo por el que existe el formulario.
- **Mismo camino que ya funcionaba.** HTTPS al 443, igual que Resend.

El canal de correo **no se elimina**: sigue disponible añadiendo `email` a
`NOTIFY_CHANNELS`, con los dos backends ya escritos y probados (Resend y SMTP).

**Varios canales, y qué cuenta como entregado.** Con dos canales activos el
aviso sale por ambos, y un canal caído no impide el envío por el otro — si no
fuera así, tener dos duplicaría la superficie de fallo sin ganar nada. El
mensaje se da por entregado con que **uno** lo consiga; solo se marca como no
entregado cuando fallan todos, que es el único caso en que nadie se entera.
Cada fallo se registra por separado con el nombre del canal: un canal roto
mientras el otro funciona no produce ningún síntoma visible, y ese es
justamente el fallo que ya costó dos rondas.

**Consecuencia de diseño.** Se separa *qué se dice* de *cómo se entrega*. El
módulo de contacto compone una `Notification` con datos estructurados —título,
pares etiqueta/valor, cuerpo— y `core/notifications.py` decide el canal. Sumar
uno nuevo es una clase y una línea en `CANALES`; el formulario no se entera.

Los datos viajan **sin maquetar** a propósito: Telegram solo acepta un
subconjunto de HTML que no incluye `<h2>`, `<p>` ni `<hr>`, así que reutilizar
el HTML del correo habría llegado como etiquetas literales.

**Un descuido que cazó una prueba.** El token del bot viaja **dentro de la
URL**, y el texto de las excepciones de `requests` incluye la URL. El
notificador de Telegram lo limpiaba antes de registrarlo, pero al añadir el
bucle multicanal éste volvía a registrar la excepción *original* — y con ella
la credencial. La corrección no fue limpiar también en el bucle, sino que el
notificador lance una excepción ya saneada (`ErrorDeEntrega`): quien conoce la
credencial es el único que puede garantizar que no se escape, y cualquier
código que la registre después queda a salvo sin tener que saberlo.

**Lección de método.** Las tres veces el fallo fue el mismo en el fondo: el
aviso no salía y **parecía que sí**. El mensaje se guardaba, la petición
devolvía 201 y el error quedaba en un registro que nadie lee. Por eso ahora el
arranque en producción se niega si faltan las credenciales del canal elegido:
un aviso que no avisa es peor que uno que falla a gritos.
