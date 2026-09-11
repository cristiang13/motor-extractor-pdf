"""Orden de lectura en un PDF a 2 columnas.

Fixture: tests/fixtures/02_two_column_pdflatex.pdf (ver
tests/fixtures/README.md). 3 páginas, layout LaTeX de 2 columnas limpio:
título/autor/fecha centrados arriba, columna izquierda (x0=72),
columna derecha (x0=310.6), número de página centrado abajo.
"""

from pdf_engine import extract_document
from tests.conftest import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "02_two_column_pdflatex.pdf"

EXPECTED_ORDER_PREFIXES = [
    "Two-Column Document with Lorem Ipsum",
    "Your Name",
    "January 3, 2024",
    "Abstract",
    "This is a sample document with two colum",
    "Lorem ipsum dolor sit amet, consectetuer",
    "Nam dui ligula, fringilla a, euismod sod",
    "Nulla malesuada porttitor diam. Donec fe",
    "pellentesque ante. Phasellus adipiscing ",
    "Quisque ullamcorper placerat ipsum. Cras",
    "Fusce mauris.",
    "1",
]


def test_reads_preamble_then_left_column_then_right_column_then_footer():
    document = extract_document(FIXTURE)
    page = document.pages[0]

    assert len(page.blocks) == len(EXPECTED_ORDER_PREFIXES)
    for block, expected_prefix in zip(page.blocks, EXPECTED_ORDER_PREFIXES, strict=True):
        assert block.text.startswith(expected_prefix)
    assert [block.reading_order for block in page.blocks] == list(range(len(page.blocks)))


def test_left_column_blocks_come_before_right_column_blocks():
    document = extract_document(FIXTURE)
    page = document.pages[0]
    # columna izquierda real: x0=72.0 (excluye titulo/autor/fecha, que estan centrados)
    left = [b for b in page.blocks if round(b.bbox.x0) == 72]
    # columna derecha real: x0=310.6
    right = [b for b in page.blocks if round(b.bbox.x0) == 311]
    assert left and right
    assert max(b.reading_order for b in left) < min(b.reading_order for b in right)


def test_two_column_detection_holds_on_pages_with_dual_column_content():
    # paginas 1 y 2 tienen texto en ambas columnas. La pagina 3 es distinta
    # a proposito: solo trae una tabla en un unico bloque ancho (x0=78) mas
    # el numero de pagina — no hay contenido real en la columna derecha, asi
    # que order_page() cae a order_single_column ahi (comportamiento
    # correcto, no un caso de 2 columnas).
    document = extract_document(FIXTURE)
    for page in document.pages[:2]:
        x0s = {round(b.bbox.x0) for b in page.blocks if b.bbox.x1 - b.bbox.x0 > 20}
        assert any(x0 < 200 for x0 in x0s)
        assert any(x0 > 300 for x0 in x0s)
