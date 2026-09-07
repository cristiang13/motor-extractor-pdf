"""Orden de lectura para documentos a 1 columna.

Heurística: de arriba hacia abajo (bbox.y0), con el borde izquierdo
(bbox.x0) como desempate. Válida solo para 1 columna — un layout a 2
columnas intercalaría los bloques de ambas columnas por altura en vez de
terminar la izquierda antes de empezar la derecha. Ese caso se resuelve en
una heurística aparte (ver CLAUDE.md, Fase 1 punto 2).
"""

from __future__ import annotations

from dataclasses import replace

from pdf_engine.models import Block


def order_single_column(blocks: list[Block]) -> list[Block]:
    ordered = sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
    return [replace(b, reading_order=i) for i, b in enumerate(ordered)]
