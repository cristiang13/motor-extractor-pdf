"""Función pública de extracción: PDF -> Document."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pymupdf

from pdf_engine.extraction.blocks import extract_raw_blocks
from pdf_engine.extraction.reading_order import order_page
from pdf_engine.models import BlockType, Document, Page


def extract_document(source: Path | bytes) -> Document:
    """Extrae bloques y orden de lectura de cada página de un PDF.

    `source` es un path a archivo o los bytes del PDF ya leídos. El orden
    de lectura por página lo decide order_page(): 1 columna o 2 columnas
    según lo que detecte geométricamente (ver
    extraction/reading_order.py).
    """
    pdf = (
        pymupdf.open(stream=source, filetype="pdf")
        if isinstance(source, bytes)
        else pymupdf.open(source)
    )
    with pdf:
        pages: list[Page] = []
        # pdf[i] en vez de enumerate(pdf): los stubs de pymupdf no declaran
        # Document como Iterable, aunque en tiempo de ejecucion si lo es.
        for index in range(len(pdf)):
            pdf_page = pdf[index]
            raw_blocks = extract_raw_blocks(pdf_page)
            width, height = cast(
                "tuple[float, float]",
                (pdf_page.rect.width, pdf_page.rect.height),  # pyright: ignore[reportUnknownMemberType]
            )
            ordered_blocks = order_page(raw_blocks, width)
            # requires_ocr a partir de los bloques ya extraidos (bloques de
            # imagen no cuentan como texto): evita una segunda pasada de
            # get_text() sobre la pagina completa solo para este chequeo.
            has_text = any(
                block.text.strip() for block in raw_blocks if block.type != BlockType.IMAGE
            )
            pages.append(
                Page(
                    number=index + 1,
                    width=width,
                    height=height,
                    blocks=ordered_blocks,
                    requires_ocr=not has_text,
                )
            )
    return Document(pages=pages)
