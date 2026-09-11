"""Detección de header/footer por repetición posicional entre páginas.

Fixtures:
- 01_single_column_pdflatex.pdf: caso simple, footer = solo número de
  página (mismo texto salvo dígito, misma posición en las 4 páginas).
- 03_federal_register_3col_header_footer.pdf: documento real (US Federal
  Register) con footer literal repetido en las 15 páginas y un header que
  alterna de posición según página par/impar — caso real con matices.
- 05_table_warn_layoff_report.pdf: caso que rompe la heurística "a
  propósito" (documentado desde el Paso 3): filas de tabla que continúan
  entre páginas, sin ningún header/footer real. Sirve para confirmar que
  la heurística NO genera falsos positivos ahí.
"""

from pdf_engine import BlockType, Page, classify_header_footer, extract_document
from tests.conftest import FIXTURES_DIR


def test_page_number_footer_detected_across_all_pages():
    document = extract_document(FIXTURES_DIR / "01_single_column_pdflatex.pdf")
    result = classify_header_footer(document)

    for page in result.pages:
        page_number_block = page.blocks[1]
        assert page_number_block.text == str(page.number)
        assert page_number_block.type == BlockType.HEADER_FOOTER
        # el parrafo de cuerpo no se toca
        assert page.blocks[0].type == BlockType.UNKNOWN


def test_document_with_fewer_than_two_pages_is_unchanged():
    document = extract_document(FIXTURES_DIR / "04_table_india_budget.pdf")
    result = classify_header_footer(document)
    assert result == document


def test_federal_register_footer_detected_on_every_page():
    document = extract_document(FIXTURES_DIR / "03_federal_register_3col_header_footer.pdf")
    result = classify_header_footer(document)

    for page in result.pages:
        footer_blocks = [
            b for b in page.blocks if b.type == BlockType.HEADER_FOOTER and "VerDate" in b.text
        ]
        assert len(footer_blocks) == 1, f"pagina {page.number} sin footer detectado"


def test_federal_register_header_detected_on_most_but_not_first_page():
    # limite conocido, documentado en classify_header_footer: el header de
    # la pagina 1 esta partido en bloques distintos a las demas paginas
    # (el numero de pagina no viene fusionado con el titulo), asi que el
    # texto normalizado no coincide y esa pagina no se detecta.
    document = extract_document(FIXTURES_DIR / "03_federal_register_3col_header_footer.pdf")
    result = classify_header_footer(document)

    def has_running_header(page: Page) -> bool:
        return any(
            b.type == BlockType.HEADER_FOOTER and "Federal Register / Vol." in b.text
            for b in page.blocks
        )

    assert not has_running_header(result.pages[0])
    assert all(has_running_header(page) for page in result.pages[1:])


def test_warn_report_table_continuation_is_not_misdetected_as_header_footer():
    # caso limite documentado desde el Paso 3 (tests/fixtures/README.md):
    # cada pagina de este reporte continua filas de tabla que empiezan en
    # la pagina anterior, sin header/footer real. La heuristica no debe
    # generar falsos positivos aca.
    document = extract_document(FIXTURES_DIR / "05_table_warn_layoff_report.pdf")
    result = classify_header_footer(document)
    assert result == document
    for page in result.pages:
        assert all(b.type != BlockType.HEADER_FOOTER for b in page.blocks)


def test_does_not_reclassify_blocks_already_typed_by_other_heuristics():
    document = extract_document(FIXTURES_DIR / "01_single_column_pdflatex.pdf")
    from dataclasses import replace

    pre_tagged = replace(
        document,
        pages=[
            replace(
                page,
                blocks=[replace(b, type=BlockType.IMAGE) for b in page.blocks],
            )
            for page in document.pages
        ],
    )
    result = classify_header_footer(pre_tagged)
    assert result == pre_tagged
