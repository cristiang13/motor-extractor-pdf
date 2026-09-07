"""Caso base: extracción de bloques + orden de lectura en un PDF a 1 columna.

Fixture: tests/fixtures/01_single_column_pdflatex.pdf (ver
tests/fixtures/README.md). 4 páginas, cada una con un bloque de párrafo y,
debajo, un bloque de número de página.
"""

from pdf_engine import BlockType, extract_document
from tests.conftest import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "01_single_column_pdflatex.pdf"


def test_extracts_one_page_per_pdf_page():
    document = extract_document(FIXTURE)
    assert len(document.pages) == 4
    assert [page.number for page in document.pages] == [1, 2, 3, 4]


def test_page_geometry_matches_pdf():
    document = extract_document(FIXTURE)
    page = document.pages[0]
    assert page.width == 595.2760009765625
    assert page.height == 841.8900146484375


def test_reading_order_is_top_to_bottom():
    document = extract_document(FIXTURE)
    for page in document.pages:
        assert len(page.blocks) == 2
        paragraph, page_number = page.blocks
        assert paragraph.reading_order == 0
        assert page_number.reading_order == 1
        # el párrafo empieza más arriba que el número de página
        assert paragraph.bbox.y0 < page_number.bbox.y0


def test_paragraph_text_is_extracted_per_page():
    document = extract_document(FIXTURE)
    expected_first_word = {
        1: "Hello, here is some text without a meaning.",
        2: "information. Really?",
        3: "you information about the selected font",
        4: "in of the original language.",
    }
    for page in document.pages:
        paragraph = page.blocks[0]
        assert paragraph.text.startswith(expected_first_word[page.number])


def test_page_number_footer_block_text():
    document = extract_document(FIXTURE)
    for page in document.pages:
        page_number_block = page.blocks[1]
        assert page_number_block.text == str(page.number)


def test_blocks_are_untyped_until_classification_runs():
    # extraction/ no clasifica párrafo vs. header/footer vs. tabla: eso lo
    # hace classification/ (todavía no implementado). Un bloque de texto
    # crudo queda como UNKNOWN.
    document = extract_document(FIXTURE)
    for page in document.pages:
        assert all(block.type == BlockType.UNKNOWN for block in page.blocks)


def test_pages_with_extractable_text_do_not_require_ocr():
    document = extract_document(FIXTURE)
    assert all(not page.requires_ocr for page in document.pages)


def test_accepts_bytes_source_not_only_path():
    pdf_bytes = FIXTURE.read_bytes()
    document = extract_document(pdf_bytes)
    assert len(document.pages) == 4
