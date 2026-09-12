"""El Markdown del admin acaba como HTML en la página: hay que sanearlo."""

import re

from core.markdown import estimate_reading_minutes, render_markdown


def test_script_tags_are_removed():
    """Escenario: cuenta de admin comprometida intentando XSS persistente."""
    html = render_markdown("Hola <script>alert('xss')</script> mundo")
    assert "<script>" not in html
    assert "alert" not in html or "&lt;script&gt;" not in html


def test_event_handlers_are_stripped():
    html = render_markdown('<img src="x" onerror="alert(1)">')
    assert "onerror" not in html


def test_javascript_protocol_links_are_neutralised():
    html = render_markdown("[click](javascript:alert(1))")
    assert "javascript:" not in html


def test_safe_markdown_survives():
    html = render_markdown("## Título\n\nTexto con **negrita** y `código`.")
    assert "<h2" in html
    assert "<strong>negrita</strong>" in html
    assert "<code>código</code>" in html


def test_fenced_code_block_is_rendered_and_highlighted():
    """Pygments envuelve los tokens en <span>, así que se compara el texto plano."""
    html = render_markdown("```bash\ndocker compose up -d\n```")
    text = re.sub(r"<[^>]+>", "", html)
    assert "docker compose up -d" in text
    assert 'class="highlight"' in html  # el resaltado se aplica en el servidor


def test_external_links_get_noopener():
    """Sin rel=noopener, la página destino puede manipular la nuestra."""
    html = render_markdown("[GitHub](https://github.com/pedrinidev)")
    assert 'rel="noopener noreferrer"' in html
    assert 'target="_blank"' in html


def test_empty_input_returns_empty_string():
    assert render_markdown("") == ""
    assert render_markdown("   ") == ""


def test_reading_time_has_a_floor_of_one_minute():
    assert estimate_reading_minutes("una palabra") == 1
    assert estimate_reading_minutes("") == 1
    assert estimate_reading_minutes(" ".join(["palabra"] * 600)) == 3
