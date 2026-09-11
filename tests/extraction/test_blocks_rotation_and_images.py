"""Regresión para 3 hallazgos de /code-review sobre el Paso 4 original:

1. bbox en páginas rotadas (/Rotate) debe quedar dentro de
   [0, width] x [0, height], no en el espacio sin rotar de PyMuPDF.
2. Las imágenes embebidas deben aparecer como BlockType.IMAGE en vez de
   desaparecer silenciosamente de la extracción.
3. requires_ocr se deriva de los bloques ya extraídos (sin una segunda
   pasada de get_text() sobre toda la página).
"""

import pymupdf

from pdf_engine import BlockType, extract_document
from pdf_engine.extraction.blocks import extract_raw_blocks
from tests.conftest import FIXTURES_DIR

SINGLE_COLUMN = FIXTURES_DIR / "01_single_column_pdflatex.pdf"
WITH_LOGO = FIXTURES_DIR / "05_table_warn_layoff_report.pdf"
SCANNED_MULTIPAGE = FIXTURES_DIR / "06_scanned_multipage.pdf"


def test_bbox_stays_within_page_bounds_after_rotation():
    with pymupdf.open(SINGLE_COLUMN) as pdf:
        page = pdf[0]
        page.set_rotation(90)  # pyright: ignore[reportUnknownMemberType]
        blocks = extract_raw_blocks(page)
        width, height = page.rect.width, page.rect.height

    assert blocks
    for block in blocks:
        assert 0 <= block.bbox.x0 <= block.bbox.x1 <= width
        assert 0 <= block.bbox.y0 <= block.bbox.y1 <= height


def test_embedded_image_is_extracted_as_image_block():
    with pymupdf.open(WITH_LOGO) as pdf:
        blocks = extract_raw_blocks(pdf[0])

    image_blocks = [b for b in blocks if b.type == BlockType.IMAGE]
    assert len(image_blocks) == 1
    assert image_blocks[0].text == ""


def test_image_blocks_do_not_count_as_extractable_text_for_requires_ocr():
    # 06 tiene paginas escaneadas puras (solo imagen) y al menos una pagina
    # (la 4) que mezcla imagen con texto real superpuesto: requires_ocr
    # tiene que distinguir ambos casos, no marcar True solo porque hay
    # bloques de imagen.
    document = extract_document(SCANNED_MULTIPAGE)
    assert document.pages[0].requires_ocr is True
    assert document.pages[3].requires_ocr is False


def test_scanned_page_has_no_unknown_text_blocks_only_image():
    with pymupdf.open(SCANNED_MULTIPAGE) as pdf:
        blocks = extract_raw_blocks(pdf[0])

    assert blocks
    assert all(b.type == BlockType.IMAGE for b in blocks)
