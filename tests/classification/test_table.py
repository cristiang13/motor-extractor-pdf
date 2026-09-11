"""Detección de tablas por alineación de columnas.

Fixtures:
- 04_table_india_budget.pdf: tabla real de cifras presupuestarias, sin
  líneas de borde dibujadas, PyMuPDF la fusiona en un único bloque de
  texto (38 filas x ~9 columnas numéricas).
- 02_two_column_pdflatex.pdf: fixture pensado para 2 columnas, pero su
  página 3 resultó tener una tabla real (verificado al implementar esta
  heurística) — bonus de cobertura no planeado.
- 01_single_column_pdflatex.pdf / 03_federal_register_3col...pdf: no
  tienen tablas reales, sirven para confirmar que un párrafo (aunque
  tenga muchas líneas) no se clasifica como tabla.
- 05_table_warn_layoff_report.pdf: caso límite conocido — la heurística
  trabaja por bloque, y en este documento PyMuPDF no segmenta la tabla
  igual en todas las páginas.
"""

from dataclasses import replace

from pdf_engine import BlockType, classify_tables, extract_document
from tests.conftest import FIXTURES_DIR

BUDGET_TABLE = FIXTURES_DIR / "04_table_india_budget.pdf"
TWO_COLUMN = FIXTURES_DIR / "02_two_column_pdflatex.pdf"
SINGLE_COLUMN = FIXTURES_DIR / "01_single_column_pdflatex.pdf"
FEDERAL_REGISTER = FIXTURES_DIR / "03_federal_register_3col_header_footer.pdf"
WARN_REPORT = FIXTURES_DIR / "05_table_warn_layoff_report.pdf"


def test_budget_table_merged_into_one_block_is_detected():
    document = extract_document(BUDGET_TABLE)
    result = classify_tables(document, BUDGET_TABLE)
    tables = [b for b in result.pages[0].blocks if b.type == BlockType.TABLE]
    assert len(tables) == 1
    assert "MINISTRY OF AGRICULTURE" in tables[0].text


def test_table_hidden_in_two_column_fixture_is_detected():
    document = extract_document(TWO_COLUMN)
    result = classify_tables(document, TWO_COLUMN)
    tables = [b for b in result.pages[2].blocks if b.type == BlockType.TABLE]
    assert len(tables) == 1
    assert "Austria" in tables[0].text


def test_plain_paragraphs_are_never_classified_as_table():
    document = extract_document(SINGLE_COLUMN)
    result = classify_tables(document, SINGLE_COLUMN)
    for page in result.pages:
        assert all(b.type != BlockType.TABLE for b in page.blocks)


def test_structured_but_non_tabular_text_is_not_misdetected():
    # direcciones, listas con bullets, bloques cortos con pocas lineas:
    # nada de esto es una tabla real, no debería dispararse.
    document = extract_document(FEDERAL_REGISTER)
    result = classify_tables(document, FEDERAL_REGISTER)
    for page in result.pages:
        assert all(b.type != BlockType.TABLE for b in page.blocks)


def test_does_not_reclassify_blocks_already_typed_by_other_heuristics():
    document = extract_document(BUDGET_TABLE)
    pre_tagged = replace(
        document,
        pages=[
            replace(
                page,
                blocks=[replace(b, type=BlockType.HEADER_FOOTER) for b in page.blocks],
            )
            for page in document.pages
        ],
    )
    result = classify_tables(pre_tagged, BUDGET_TABLE)
    assert result == pre_tagged


def test_warn_report_known_limitation_depends_on_pymupdf_block_segmentation():
    # Limite conocido: la heuristica trabaja por bloque tal como lo
    # segmenta PyMuPDF, sin fusionar bloques adyacentes. En este reporte,
    # PyMuPDF junta toda la tabla en un solo bloque en algunas paginas
    # (se detectan) pero en otras arma un bloque por fila (cada uno con
    # muy pocas lineas, nunca llega al minimo de filas para "tabla") — no
    # se intenta unir esos bloques en esta fase.
    document = extract_document(WARN_REPORT)
    result = classify_tables(document, WARN_REPORT)

    def page_has_table(page_number: int) -> bool:
        page = result.pages[page_number - 1]
        return any(b.type == BlockType.TABLE for b in page.blocks)

    detected = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}
    not_detected = {2, 15, 16}
    assert all(page_has_table(p) for p in detected)
    assert all(not page_has_table(p) for p in not_detected)
