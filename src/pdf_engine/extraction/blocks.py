"""Extracción de bloques crudos de una página de PyMuPDF, sin orden de lectura asignado."""

from __future__ import annotations

from typing import cast

import pymupdf

from pdf_engine.models import BBox, Block, BlockType

_TEXT_BLOCK = 0
_IMAGE_BLOCK = 1

# PyMuPDF trae py.typed pero sus firmas reales (get_text con overloads segun
# el string de formato, atributos de Rect, etc.) no estan completamente
# tipadas: el retorno se resuelve a tipos parcialmente Unknown para pyright
# estricto. RawBlock documenta la forma real de cada tupla que devuelve
# get_text("blocks") y el cast() aisla ese limite en un solo lugar en vez de
# propagar Unknown por todo el modulo.
RawBlock = tuple[float, float, float, float, str, int, int]


def extract_raw_blocks(page: pymupdf.Page) -> list[Block]:
    """Bloques de una página en el orden que devuelve PyMuPDF (no es orden de
    lectura confiable para layouts con columnas). Cada bloque de texto queda
    con type=UNKNOWN: la clasificación en paragraph/table/header_footer la
    hace classification/, no este módulo. reading_order se deja en 0 para
    todos; lo asigna extraction/reading_order.py."""
    raw_blocks = cast(
        "list[RawBlock]",
        page.get_text("blocks"),  # pyright: ignore[reportUnknownMemberType]
    )
    blocks: list[Block] = []
    for x0, y0, x1, y1, text, _block_no, block_type in raw_blocks:
        kind = BlockType.IMAGE if block_type == _IMAGE_BLOCK else BlockType.UNKNOWN
        blocks.append(
            Block(
                bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                text=text.strip("\n"),
                type=kind,
                reading_order=0,
            )
        )
    return blocks
