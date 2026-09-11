"""Detección de tablas por alineación de columnas (sin ML).

A diferencia de classify_header_footer, esta heurística necesita más
detalle que el que guarda un Block: PyMuPDF suele fusionar una tabla
entera en un solo bloque de texto (una tabla de presupuesto real de 38
filas x ~9 columnas queda como 1 solo bloque). Para detectar columnas hace
falta la posición de cada palabra dentro de ese bloque, no solo su bbox
total — por eso classify_tables() recibe también `source` (path o bytes)
y vuelve a abrir el PDF con PyMuPDF para consultar `get_text("words",
clip=bbox)` por cada bloque candidato.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from typing import cast

import pymupdf

from pdf_engine.models import Block, BlockType, Document, Page

# Palabra separada de la anterior por al menos esta distancia (puntos): se
# considera el inicio de una columna nueva, no una simple separación entre
# palabras de la misma oración.
_COLUMN_GAP_THRESHOLD = 8.0

# Tolerancia en puntos para agrupar inicios de columna "en la misma posición".
_COLUMN_X_TOLERANCE = 5.0

# Una posición de columna cuenta si aparece en al menos esta fraccion de
# las filas del bloque (con un piso absoluto de filas).
_MIN_ROW_FRACTION = 0.3
_MIN_ROWS_ABS = 4

# Un bloque necesita al menos esta cantidad de filas y de columnas
# recurrentes para clasificarse como tabla.
_MIN_ROWS_FOR_TABLE = 4
_MIN_COLUMNS_FOR_TABLE = 3

Word = tuple[float, float, float, float, str, int, int, int]


def classify_tables(document: Document, source: Path | bytes) -> Document:
    """Devuelve un Document nuevo con los bloques que parecen tabla
    re-tipados a BlockType.TABLE. Solo evalúa bloques todavía UNKNOWN —
    no pisa clasificaciones de otras heurísticas (correr
    classify_header_footer antes evita que un footer multi-línea se
    evalúe acá, aunque en la práctica esos bloques son demasiado cortos
    para pasar el umbral de filas de todos modos).

    Heurística: agrupa las palabras de un bloque en filas por su
    coordenada y0, y por cada fila registra los "inicios de columna" — la
    primera palabra de la fila, más cualquier palabra separada de la
    anterior por un espacio en blanco de al menos 8pt (más ancho que un
    espacio normal entre palabras). Si al menos 3 posiciones de inicio de
    columna se repiten en una fracción suficiente de las filas, el bloque
    tiene estructura de tabla.

    Validado contra PDFs reales: un párrafo normal (justificado o no)
    nunca junta 3+ posiciones de columna recurrentes — como mucho el
    margen izquierdo se repite en casi todas las líneas, que cuenta como
    una sola columna. Tablas reales sin líneas de borde dibujadas
    (`04_table_india_budget.pdf`, cifras alineadas por espacios) sí las
    tienen.
    """
    pdf = (
        pymupdf.open(stream=source, filetype="pdf")
        if isinstance(source, bytes)
        else pymupdf.open(source)
    )
    with pdf:
        new_pages: list[Page] = []
        for page_index, page in enumerate(document.pages):
            pdf_page = pdf[page_index]
            new_blocks = [
                replace(block, type=BlockType.TABLE)
                if block.type == BlockType.UNKNOWN and _looks_like_table(pdf_page, block)
                else block
                for block in page.blocks
            ]
            new_pages.append(replace(page, blocks=new_blocks))
    return Document(pages=new_pages)


def _looks_like_table(pdf_page: pymupdf.Page, block: Block) -> bool:
    clip = pymupdf.Rect(block.bbox.x0, block.bbox.y0, block.bbox.x1, block.bbox.y1)
    words = cast(
        "list[Word]",
        pdf_page.get_text("words", clip=clip),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    )
    if not words:
        return False

    rows = _group_into_rows(words)
    if len(rows) < _MIN_ROWS_FOR_TABLE:
        return False

    column_rows: dict[float, set[int]] = defaultdict(set)
    for row_index, row_words in enumerate(rows):
        for x in _column_starts(row_words):
            key = round(x / _COLUMN_X_TOLERANCE) * _COLUMN_X_TOLERANCE
            column_rows[key].add(row_index)

    min_rows = max(_MIN_ROWS_ABS, int(len(rows) * _MIN_ROW_FRACTION))
    recurring_columns = sum(1 for locations in column_rows.values() if len(locations) >= min_rows)
    return recurring_columns >= _MIN_COLUMNS_FOR_TABLE


def _group_into_rows(words: list[Word], y_tolerance: float = 2.0) -> list[list[Word]]:
    rows: list[tuple[float, list[Word]]] = []
    for word in sorted(words, key=lambda w: w[1]):
        for row_y, row_words in rows:
            if abs(row_y - word[1]) <= y_tolerance:
                row_words.append(word)
                break
        else:
            rows.append((word[1], [word]))
    return [row_words for _y, row_words in rows]


def _column_starts(row_words: list[Word]) -> list[float]:
    ordered = sorted(row_words, key=lambda w: w[0])
    starts = [ordered[0][0]]
    for previous, current in pairwise(ordered):
        gap = current[0] - previous[2]
        if gap >= _COLUMN_GAP_THRESHOLD:
            starts.append(current[0])
    return starts
