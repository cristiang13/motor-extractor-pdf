"""Función pública de extracción: PDF -> Document."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pymupdf

from pdf_engine.extraction.blocks import extract_raw_blocks
from pdf_engine.extraction.reading_order import order_single_column
from pdf_engine.models import Document, Page


def extract_document(source: Path | bytes) -> Document:
    """Extrae bloques y orden de lectura de cada página de un PDF.

    `source` es un path a archivo o los bytes del PDF ya leídos. Asume
    layout a 1 columna (order_single_column); el soporte para 2 columnas se
    agrega en una heurística aparte que decide, por página, qué función de
    orden usar.
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
            ordered_blocks = order_single_column(raw_blocks)
            page_text = cast(
                "str",
                pdf_page.get_text("text"),  # pyright: ignore[reportUnknownMemberType]
            )
            width, height = cast(
                "tuple[float, float]",
                (pdf_page.rect.width, pdf_page.rect.height),  # pyright: ignore[reportUnknownMemberType]
            )
            pages.append(
                Page(
                    number=index + 1,
                    width=width,
                    height=height,
                    blocks=ordered_blocks,
                    requires_ocr=not page_text.strip(),
                )
            )
    return Document(pages=pages)
