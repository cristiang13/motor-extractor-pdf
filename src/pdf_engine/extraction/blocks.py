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
    todos; lo asigna extraction/reading_order.py.

    get_text("blocks") devuelve bbox en el espacio sin rotar de la página,
    aunque la página tenga /Rotate — Page.rect (y por lo tanto
    Page.width/height) sí refleja esa rotación, así que sin corregir esto
    los bbox de páginas rotadas quedan fuera de [0,width]x[0,height].
    Se corrige multiplicando cada bbox por page.rotation_matrix, la matriz
    que PyMuPDF expone justo para pasar de coordenadas sin rotar a
    coordenadas de página rotada.

    Se pasa TEXT_PRESERVE_IMAGES además de los flags default de bloques:
    sin ese flag, get_text("blocks") nunca devuelve bloques de imagen
    (block_type=1) y BlockType.IMAGE queda sin usar — cualquier imagen
    embebida (logo, sello, firma) desaparece de la extracción en vez de
    quedar como un bloque IMAGE."""
    flags = pymupdf.TEXTFLAGS_BLOCKS | pymupdf.TEXT_PRESERVE_IMAGES  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    raw_blocks = cast(
        "list[RawBlock]",
        page.get_text("blocks", flags=flags),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    )
    rotation_matrix = page.rotation_matrix  # pyright: ignore[reportUnknownMemberType]
    blocks: list[Block] = []
    for x0, y0, x1, y1, text, _block_no, block_type in raw_blocks:
        bbox = pymupdf.Rect(x0, y0, x1, y1) * rotation_matrix
        # Rect.x0/y0/x1/y1 quedan parcialmente Unknown en el stub de pymupdf
        # (ver comentario de RawBlock arriba); float() los deja concretos.
        rotated = (
            float(bbox.x0),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            float(bbox.y0),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            float(bbox.x1),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            float(bbox.y1),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        is_image = block_type == _IMAGE_BLOCK
        blocks.append(
            Block(
                bbox=BBox(x0=rotated[0], y0=rotated[1], x1=rotated[2], y1=rotated[3]),
                text="" if is_image else text.strip("\n"),
                type=BlockType.IMAGE if is_image else BlockType.UNKNOWN,
                reading_order=0,
            )
        )
    return blocks
