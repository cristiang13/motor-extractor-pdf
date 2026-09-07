"""Dataclasses compartidas entre extraction/, classification/ y rendering/."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BlockType(StrEnum):
    """Tipo de bloque. PARAGRAPH y HEADER_FOOTER los asigna classification/;
    extraction/ solo distingue IMAGE (estructural) de UNKNOWN (texto sin
    clasificar todavía)."""

    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    HEADER_FOOTER = "header_footer"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BBox:
    """Rectángulo en coordenadas de página PDF (origen arriba-izquierda, en puntos)."""

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class Block:
    bbox: BBox
    text: str
    type: BlockType
    reading_order: int


@dataclass(frozen=True)
class Page:
    number: int
    width: float
    height: float
    blocks: list[Block]
    requires_ocr: bool


@dataclass(frozen=True)
class Document:
    pages: list[Page]
