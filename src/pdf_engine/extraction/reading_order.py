"""Orden de lectura: 1 columna (caso base) y 2 columnas (detección + orden).

order_page() es el punto de entrada que usa extraction/document.py: decide
por página si aplica el orden simple o el de 2 columnas.
"""

from __future__ import annotations

from dataclasses import replace

from pdf_engine.models import Block

# Tolerancia en puntos para considerar que dos bloques "centrados" (fuera
# de las columnas detectadas) arrancan en la misma posición horizontal, y
# por lo tanto podrían ser en realidad una columna que la heurística no
# reconoció como tal (ver _looks_like_hidden_column).
_COLUMN_X_TOLERANCE = 5.0

# Un bloque "centrado" más ancho que esta fracción del ancho de página se
# asume header/footer/título real, no una columna angosta mal clasificada.
_MAX_COLUMN_BLOCK_WIDTH_RATIO = 0.4


def _by_position(block: Block) -> tuple[float, float]:
    return (block.bbox.y0, block.bbox.x0)


def order_single_column(blocks: list[Block]) -> list[Block]:
    """De arriba hacia abajo (bbox.y0), bbox.x0 como desempate.

    Válida por sí sola solo para 1 columna: en 2 columnas intercalaría
    bloques de ambas por altura en vez de agotar la izquierda antes de
    empezar la derecha. order_page() la usa como fallback cuando no
    detecta 2 columnas confiables en la página.
    """
    ordered = sorted(blocks, key=_by_position)
    return [replace(b, reading_order=i) for i, b in enumerate(ordered)]


def order_page(blocks: list[Block], page_width: float) -> list[Block]:
    """Detecta 1 vs 2 columnas en la página y ordena en consecuencia.

    Heurística geométrica (sin ML): calcula la línea media a partir del
    contenido real de la página (min x0 / max x1 de todos los bloques, no
    page_width/2 — el gutter real no siempre cae en el centro geométrico
    de la página) y clasifica cada bloque como IZQUIERDA (x1 <= línea
    media), DERECHA (x0 >= línea media) o CENTRADO (cruza la línea media:
    título, autor, número de página, header/footer).

    Si hay bloques a ambos lados, asume 2 columnas y ordena: bloques
    centrados arriba de las columnas -> columna izquierda de arriba a
    abajo -> columna derecha de arriba a abajo -> bloques centrados abajo
    de las columnas. Un bloque centrado cuyo y0 cae dentro del rango
    vertical de las columnas (interleaved) se asigna a "arriba" o "abajo"
    según a cuál mitad está más cerca — límite conocido para headers que
    aparecen a mitad de página.

    Límite conocido más importante (ver CLAUDE.md): en un layout de 3+
    columnas, la columna del medio puede terminar clasificada como
    CENTRADA en vez de como columna propia. Para no producir un orden
    incorrecto con apariencia de correcto, _looks_like_hidden_column
    detecta ese caso (varios bloques centrados angostos alineados entre
    sí, como una columna oculta) y hace caer toda la página a
    order_single_column en vez de aplicar el orden de 2 columnas.
    """
    if not blocks:
        return []

    left_edge = min(b.bbox.x0 for b in blocks)
    right_edge = max(b.bbox.x1 for b in blocks)
    midline = (left_edge + right_edge) / 2

    left_blocks: list[Block] = []
    right_blocks: list[Block] = []
    centered_blocks: list[Block] = []
    for block in blocks:
        if block.bbox.x1 <= midline:
            left_blocks.append(block)
        elif block.bbox.x0 >= midline:
            right_blocks.append(block)
        else:
            centered_blocks.append(block)

    if not left_blocks or not right_blocks:
        return order_single_column(blocks)

    if _looks_like_hidden_column(centered_blocks, page_width):
        return order_single_column(blocks)

    column_top = min(b.bbox.y0 for b in left_blocks + right_blocks)
    column_bottom = max(b.bbox.y1 for b in left_blocks + right_blocks)
    column_mid = (column_top + column_bottom) / 2

    above = [b for b in centered_blocks if b.bbox.y0 < column_mid]
    below = [b for b in centered_blocks if b.bbox.y0 >= column_mid]

    ordered = (
        sorted(above, key=_by_position)
        + sorted(left_blocks, key=_by_position)
        + sorted(right_blocks, key=_by_position)
        + sorted(below, key=_by_position)
    )
    return [replace(b, reading_order=i) for i, b in enumerate(ordered)]


def _looks_like_hidden_column(centered_blocks: list[Block], page_width: float) -> bool:
    groups: dict[float, list[Block]] = {}
    for block in centered_blocks:
        width = block.bbox.x1 - block.bbox.x0
        if width > page_width * _MAX_COLUMN_BLOCK_WIDTH_RATIO:
            continue  # ancho de header/footer real, no columna angosta
        key = round(block.bbox.x0 / _COLUMN_X_TOLERANCE) * _COLUMN_X_TOLERANCE
        groups.setdefault(key, []).append(block)
    return any(len(group) >= 2 for group in groups.values())
