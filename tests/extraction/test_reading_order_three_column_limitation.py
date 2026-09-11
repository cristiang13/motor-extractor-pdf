"""Caso límite conocido: layout de 3 columnas (no cubierto en Fase 1).

Fixture: tests/fixtures/03_federal_register_3col_header_footer.pdf — una
regla propuesta real del US Federal Register, con 3 columnas (x0 en 45,
222 y 399) más header/footer repetido. order_page() solo detecta 1 y 2
columnas (alcance de Fase 1); en 3+ columnas la columna del medio (x0=222)
puede terminar clasificada como "centrada", así que la heurística de
columna oculta (_looks_like_hidden_column) descarta el orden de 2 columnas
y cae a order_single_column sobre toda la página.

Este test no verifica que el orden sea "correcto" (no lo es: mezcla texto
de las 3 columnas por altura) — fija el comportamiento de fallback como
límite conocido y documentado, no como bug silencioso. Si se agrega
soporte a 3+ columnas en una fase futura, este test debería actualizarse
para reflejar el nuevo comportamiento.
"""

import pymupdf

from pdf_engine import extract_document
from pdf_engine.extraction.blocks import extract_raw_blocks
from pdf_engine.extraction.reading_order import order_page, order_single_column
from tests.conftest import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "03_federal_register_3col_header_footer.pdf"


def test_page_has_three_distinct_column_positions():
    # confirma la premisa del test: esta pagina real tiene 3 columnas, no 2
    with pymupdf.open(FIXTURE) as pdf:
        blocks = extract_raw_blocks(pdf[0])
    x0s = {round(b.bbox.x0) for b in blocks if b.bbox.x1 - b.bbox.x0 > 20}
    assert {45, 222, 399} <= x0s


def test_three_column_page_falls_back_to_single_column_order():
    with pymupdf.open(FIXTURE) as pdf:
        page = pdf[0]
        raw_blocks = extract_raw_blocks(page)
        width = page.rect.width

    result = order_page(raw_blocks, width)
    expected_fallback = order_single_column(raw_blocks)

    assert [b.text for b in result] == [b.text for b in expected_fallback]


def test_fallback_order_does_not_read_columns_in_order():
    # evidencia de la limitacion: el bloque de la columna 2 (x0=222) que
    # queda antes del final de la columna 1 (x0=45) en altura se intercala
    # en vez de esperar a que termine la columna 1 completa.
    document = extract_document(FIXTURE)
    page = document.pages[0]
    x0_sequence = [round(b.bbox.x0) for b in page.blocks]
    first_col2_index = next(i for i, x0 in enumerate(x0_sequence) if x0 == 222)
    last_col1_index = max(i for i, x0 in enumerate(x0_sequence) if x0 == 45)
    assert first_col2_index < last_col1_index
