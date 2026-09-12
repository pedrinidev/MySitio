"""Conversión de Markdown a HTML seguro.

El HTML se genera **al guardar**, no al servir: renderizar el mismo texto en
cada petición es trabajo repetido que se paga en CPU de un droplet que solo
tiene un núcleo.

El resultado se sanea aunque el único autor sea el dueño del sitio. Motivo: si
alguna vez roban esa cuenta de admin, el ataque queda en "puede publicar texto
raro" en lugar de "puede inyectar JavaScript persistente en cada visitante".
Defensa en profundidad, no desconfianza del autor.
"""

from __future__ import annotations

import bleach
import markdown as md
from django.utils.functional import keep_lazy_text

_EXTENSIONS = [
    "extra",  # tablas, bloques cercados, notas al pie, listas de definición
    "admonition",
    "sane_lists",
    "toc",
    "codehilite",
]

_EXTENSION_CONFIGS = {
    "codehilite": {
        # Resaltado en el servidor: cero JavaScript en el cliente para algo
        # que nunca cambia después de publicado.
        "css_class": "highlight",
        "guess_lang": False,
        "linenums": False,
    },
    "toc": {"permalink": False},
}

ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "hr",
        "span",
        "div",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "em",
        "del",
        "sub",
        "sup",
        "mark",
        "ul",
        "ol",
        "li",
        "blockquote",
        "pre",
        "code",
        "a",
        "img",
        "figure",
        "figcaption",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "loading", "width", "height"],
    "code": ["class"],
    "pre": ["class"],
    "span": ["class"],
    "div": ["class"],
    "th": ["align", "colspan", "rowspan"],
    "td": ["align", "colspan", "rowspan"],
}

# Sin `javascript:` ni `data:`: son los dos vectores clásicos de XSS por enlace.
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# h1 se excluye a propósito: el título de la página ya es el h1. Dos h1 en un
# documento rompen la jerarquía para lectores de pantalla y para el SEO.


@keep_lazy_text
def render_markdown(text: str) -> str:
    """Convierte Markdown a HTML saneado. Cadena vacía si no hay contenido."""
    if not text or not text.strip():
        return ""

    raw_html = md.markdown(
        text,
        extensions=_EXTENSIONS,
        extension_configs=_EXTENSION_CONFIGS,
        output_format="html",
    )

    clean_html = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # Todo enlace externo se abre en pestaña nueva con rel de seguridad.
    # `noopener` impide que la página destino manipule la nuestra vía
    # window.opener — un fallo real, no teórico.
    return bleach.linkify(
        clean_html,
        callbacks=[_external_link_attrs],
        skip_tags=["pre", "code"],
        parse_email=False,
    )


def _external_link_attrs(attrs: dict, new: bool = False) -> dict:
    """Añade target y rel a los enlaces externos."""
    href = attrs.get((None, "href"), "")
    if href.startswith(("http://", "https://")):
        attrs[(None, "target")] = "_blank"
        attrs[(None, "rel")] = "noopener noreferrer"
    return attrs


def estimate_reading_minutes(text: str, words_per_minute: int = 200) -> int:
    """Minutos de lectura estimados, mínimo 1.

    200 ppm es el consenso para lectura técnica en pantalla. Devolver 0 para
    un texto corto quedaría raro en la interfaz, así que el piso es 1.
    """
    if not text:
        return 1
    return max(1, round(len(text.split()) / words_per_minute))
