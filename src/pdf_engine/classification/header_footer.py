"""Detección de encabezado/pie de página por repetición posicional entre páginas.

Heurística (sin ML): un bloque de texto cerca del borde superior o
inferior de la página se clasifica como HEADER_FOOTER si un bloque en
(aproximadamente) la misma posición, con el mismo texto salvo por dígitos
(para tolerar números de página, fechas, etc.), aparece en al menos la
mitad de las páginas del documento.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from pdf_engine.models import Block, BlockType, Document, Page

_DIGIT_RUN = re.compile(r"\d+")

# Fracción de la altura de página que cuenta como "cerca del borde"
# superior o inferior. Calibrado contra fixtures reales: 0.12 dejaba
# afuera números de página que caen justo antes del margen inferior
# (bbox.y0 al ~85% de la altura); 0.18 los cubre sin capturar contenido
# de cuerpo de página en los fixtures probados.
_EDGE_BAND_FRACTION = 0.18

# Tolerancia en puntos para considerar que dos bloques están "en la misma
# posición" entre páginas.
_POSITION_TOLERANCE = 3.0


def classify_header_footer(document: Document) -> Document:
    """Devuelve un Document nuevo con los bloques de header/footer
    detectados re-tipados a BlockType.HEADER_FOOTER. No modifica bloques
    ya clasificados (BlockType != UNKNOWN) — no pisa clasificaciones de
    otras heurísticas de classification/.

    Con menos de 2 páginas no hay "repetición entre páginas" posible: se
    devuelve el documento sin cambios.

    Límite conocido (validado con tests/fixtures/03_..._header_footer.pdf,
    un boletín real del US Federal Register): el header de esa página
    cambia de posición horizontal según si la página es par o impar
    (paginación tipo libro, encuadernado a doble página), así que en vez
    de un solo grupo de 15 páginas la heurística lo separa en 2 grupos de
    7 — igual se detectan como HEADER_FOOTER porque cada grupo por sí solo
    supera el umbral, pero es una fragmentación interna no resuelta. Y la
    primera página de ese mismo documento tiene el header partido en
    bloques distintos a las demás (el número de página no está fusionado
    con el título) — texto normalizado no coincide, esa página se queda
    sin detectar. No se intenta resolver ninguno de los dos casos en esta
    fase.
    """
    if len(document.pages) < 2:
        return document

    min_repeats = max(2, len(document.pages) // 2)

    # signature -> lista de (indice de pagina, indice de bloque en esa pagina)
    candidates: dict[tuple[float, float, str], list[tuple[int, int]]] = defaultdict(list)
    for page_index, page in enumerate(document.pages):
        top_edge = page.height * _EDGE_BAND_FRACTION
        bottom_edge = page.height * (1 - _EDGE_BAND_FRACTION)
        for block_index, block in enumerate(page.blocks):
            if block.type != BlockType.UNKNOWN:
                continue
            near_top = block.bbox.y1 <= top_edge
            near_bottom = block.bbox.y0 >= bottom_edge
            if not (near_top or near_bottom):
                continue
            candidates[_signature(block)].append((page_index, block_index))

    header_footer_locations = {
        (page_index, block_index)
        for locations in candidates.values()
        if len(locations) >= min_repeats
        for page_index, block_index in locations
    }
    if not header_footer_locations:
        return document

    new_pages: list[Page] = []
    for page_index, page in enumerate(document.pages):
        new_blocks: list[Block] = [
            replace(block, type=BlockType.HEADER_FOOTER)
            if (page_index, block_index) in header_footer_locations
            else block
            for block_index, block in enumerate(page.blocks)
        ]
        new_pages.append(replace(page, blocks=new_blocks))
    return Document(pages=new_pages)


def _signature(block: Block) -> tuple[float, float, str]:
    x0 = round(block.bbox.x0 / _POSITION_TOLERANCE) * _POSITION_TOLERANCE
    y0 = round(block.bbox.y0 / _POSITION_TOLERANCE) * _POSITION_TOLERANCE
    normalized_text = _DIGIT_RUN.sub("#", block.text.strip())
    return (x0, y0, normalized_text)
