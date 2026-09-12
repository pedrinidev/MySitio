# syntax=docker/dockerfile:1
#
# Django + DRF sobre Alpine.
#
# Alpine usa musl, y ni psutil ni Pillow publican wheels para musl: hay que
# compilarlos. Por eso el build es multi-etapa — la cadena de compilación
# (gcc, headers, paquetes -dev) pesa ~250 MB y NO puede terminar en la
# imagen final.
#
# Los wheels se consumen con `--mount=type=bind` y NO con `COPY`. La
# diferencia son ~110 MB: un COPY graba los wheels en su propia capa de forma
# permanente, y el `rm -rf` posterior solo los oculta en las capas siguientes
# sin recuperar un byte. El montaje los expone durante el RUN y no deja
# rastro en la imagen.
#
# Tamaño final medido: ~226 MB (Alpine 50 MB + Pillow, Django, Pygments y el
# resto de dependencias). Es huella de DISCO, no de RAM: en los 10 GB del
# droplet caben esta imagen, la del sitio (~25 MB) y varias versiones
# anteriores para poder revertir.

# ───────────────────────── base ─────────────────────────
FROM python:3.12-alpine AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Solo bibliotecas de EJECUCIÓN (las -dev quedan en la etapa builder).
RUN apk add --no-cache \
        libjpeg-turbo \
        zlib \
        freetype \
        libwebp \
        sqlite-libs \
        curl \
        tzdata

# ──────────────────────── builder ───────────────────────
FROM base AS builder

RUN apk add --no-cache \
        build-base \
        linux-headers \
        python3-dev \
        jpeg-dev \
        zlib-dev \
        freetype-dev \
        libwebp-dev

COPY requirements/ /tmp/requirements/

# Un único almacén de wheels que cubre dev y prod: cada etapa final
# instala solo lo que necesita, sin volver a compilar nada.
RUN pip wheel --wheel-dir /wheels \
        -r /tmp/requirements/dev.txt \
        -r /tmp/requirements/prod.txt

# ────────────────────────── dev ─────────────────────────
FROM base AS dev

RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    --mount=type=bind,source=requirements,target=/tmp/requirements \
    pip install --no-index --find-links=/wheels -r /tmp/requirements/dev.txt

# En desarrollo el código llega por bind-mount (recarga automática).
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ───────────────────────── prod ─────────────────────────
FROM base AS prod

RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    --mount=type=bind,source=requirements,target=/tmp/requirements \
    pip install --no-index --find-links=/wheels -r /tmp/requirements/prod.txt

# Usuario sin privilegios: si alguien escapa de Django, no aterriza en root.
RUN addgroup -g 1001 -S app && adduser -u 1001 -S app -G app

COPY --chown=app:app . /app

# /data es un volumen; se crea aquí para fijar el propietario correcto.
RUN mkdir -p /data/media /data/static /data/backups && chown -R app:app /data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health/ || exit 1

# gthread, no workers extra: la carga es de E/S (SQLite + SMTP), no de CPU,
# y en 512 MB cada worker adicional cuesta ~75 MB.
# --max-requests recicla workers y neutraliza fugas de memoria lentas.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--max-requests", "500", \
     "--max-requests-jitter", "50", \
     "--timeout", "30", \
     "--graceful-timeout", "20", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
