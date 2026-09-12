#!/usr/bin/env python
"""Punto de entrada de las tareas administrativas de Django."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y el entorno virtual activo?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
