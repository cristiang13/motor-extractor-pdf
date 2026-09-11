# pdf-engine

Motor Python puro para parsear documentos PDF operativos (facturas,
manifiestos, B/L, y documentos similares del ámbito marítimo/aduanero) y
extraer su contenido de forma estructurada: bloques de texto con su
posición (bbox), orden de lectura, y clasificación básica (párrafo / tabla
/ imagen / encabezado-pie de página).

Es la base de dos productos futuros que **no** se construyen en este
módulo: un extractor de campos por plantilla (ancla de texto → valor) y un
visor móvil que amplía bloques al tocarlos. El motor es una librería sin
acoplamiento a framework web, CLI, ni UI.

## Alcance de Fase 1 (actual)

1. Extracción de bloques por página: bbox, texto, tipo, orden de lectura.
2. Orden de lectura correcto en documentos a 1 y 2 columnas.
3. Detección de encabezado/pie de página por repetición posicional entre
   páginas.
4. Detección de tablas por alineación de columnas (sin ML).
5. Render de bbox → recorte de imagen escalado.
6. Detección de páginas sin texto extraíble (`requires_ocr=True`), sin
   implementar OCR.

Fuera de alcance: FastAPI/colas/DB, LLM para extracción, OCR real, capa de
plantillas (ancla → campo).

## Stack

- `uv` para entorno y dependencias.
- `pymupdf` como única dependencia de parseo.
- `ruff` para lint y formato (`uv run ruff check .`, `uv run ruff format .`).
- `pyright` en modo estricto para chequeo de tipos (`uv run pyright`).
- `pytest` para tests (`uv run pytest`).

## Arquitectura

Estructura por responsabilidad (Alternativa A, elegida sobre un `core.py`
único):

```
src/pdf_engine/
  models.py           dataclasses compartidas (Block, Page, BBox, etc.)
  extraction/          extracción de bloques crudos desde PyMuPDF + orden de lectura
  classification/       heurísticas de tipo de bloque (header/footer, tabla, párrafo)
  rendering/            bbox -> recorte de imagen escalado
```

Regla de dependencia: `extraction/`, `classification/` y `rendering/`
dependen de `models.py`, nunca al revés, y no dependen entre sí salvo que
una heurística lo requiera explícitamente (ej. `classification` consume la
salida de `extraction`, nunca en sentido inverso).

Todas las funciones públicas reciben bytes/paths y devuelven dataclasses
tipadas. Sin estado global, sin side effects fuera de I/O explícito de
lectura de archivo.

## Historial de hallazgos

### 2026-09-07
- Repositorio inicializado. Se evaluaron 2 alternativas de estructura de
  módulos (por responsabilidad vs. `core.py` único); se eligió la
  estructura por responsabilidad (`extraction/`, `classification/`,
  `rendering/` + `models.py` compartido).
- Proyecto scaffolded con `uv init --lib`, dependencia `pymupdf`, dev deps
  `ruff`/`pyright`/`pytest`. Ruff y Pyright (modo estricto) configurados y
  pasando limpio sobre el esqueleto vacío.
- Pendiente antes de escribir la primera heurística: reunir 5-8 PDFs reales
  de prueba (1 columna, 2 columnas, con tabla, escaneado, header/footer
  repetido). No se usarán fixtures sintéticas como punto de partida.
- Se reunieron 7 PDFs reales en `tests/fixtures/` (detalle y procedencia en
  `tests/fixtures/README.md`), tomados de las suites de test de
  `pdfplumber`, `camelot`, `ocrmypdf` y `py-pdf/sample-files`, más
  documentos públicos de gobierno (US Federal Register, reporte WARN de
  California, presupuesto de India). Ninguno es del dominio
  marítimo/aduanero propio del proyecto — es la mejor aproximación pública
  disponible por caso de layout; si aparecen documentos reales del dominio
  (anonimizados), se suman sin reemplazar estos. Cubren los 5 casos
  pedidos, con un caso combinado (2 columnas + header/footer repetido en
  `03_federal_register_...pdf`) y un caso límite de tabla que cruza
  páginas (`05_table_warn_layoff_report.pdf`) documentado como riesgo de
  falso positivo para la heurística de header/footer.
- Implementado el caso base de extracción: `models.py` (BBox, Block,
  BlockType, Page, Document), `extraction/blocks.py`
  (`extract_raw_blocks`), `extraction/reading_order.py`
  (`order_single_column`, heurística y0→x0, documentada como válida solo
  para 1 columna) y `extraction/document.py` (`extract_document`, función
  pública, acepta path o bytes). `extraction/` asigna `BlockType.UNKNOWN` a
  todo bloque de texto — la clasificación en paragraph/table/header_footer
  la hace `classification/`, que todavía no existe. `requires_ocr` por
  página se calcula ya en esta función (texto extraíble vacío), no hace
  falta una heurística aparte para eso.
- Límite conocido: los stubs (`py.typed`) que trae `pymupdf` están
  incompletos — `get_text()`, `Rect.width/height` y la iteración de
  `Document` no quedan tipados en modo estricto. Se resolvió con
  `typing.cast` explícito (tipo `RawBlock` documentando la forma real de
  cada tupla) más `# pyright: ignore[reportUnknownMemberType]` acotado a
  la línea exacta de la llamada, en vez de bajar `typeCheckingMode` o
  ignorar el archivo completo. Test suite del caso 1 columna
  (`tests/extraction/test_document_single_column.py`, fixture
  `01_single_column_pdflatex.pdf`) pasando, Ruff y Pyright estricto
  limpios.

### 2026-09-11
- Corrección de un hallazgo anterior: `tests/fixtures/03_...pdf` no es un
  documento a 2 columnas — es a **3** columnas (x0 en 45, 222 y 399 pt).
  Se descubrió al implementar la heurística de 2 columnas, verificando
  bbox reales en vez de solo el conteo aproximado de palabras
  izquierda/derecha que se usó en el Paso 3. Se renombró a
  `03_federal_register_3col_header_footer.pdf` y se reutilizó como el
  caso límite de "3+ columnas, fuera de alcance" en vez de caso base de
  2 columnas.
- Implementado soporte de 2 columnas: `extraction/reading_order.py` ahora
  expone `order_page(blocks, page_width)`, el punto de entrada que usa
  `extraction/document.py` (reemplaza la llamada directa a
  `order_single_column`). Heurística geométrica: línea media calculada
  del contenido real de la página (min x0 / max x1 de los bloques, no
  `page_width/2` — el gutter real no siempre cae en el centro geométrico,
  confirmado con el fixture 02), bloques clasificados en
  izquierda/derecha/centrado según si cruzan esa línea. Si hay bloques a
  ambos lados: centrados-arriba (título/autor/fecha) -> columna izquierda
  -> columna derecha -> centrados-abajo (pie de página). Si no hay
  bloques a ambos lados, cae a `order_single_column` sin cambios (no
  rompe el caso de 1 columna, los 8 tests de esa fase siguen pasando
  intactos).
- Límite conocido y decidido a propósito: **no se intentó soportar 3+
  columnas**. En vez de eso, `_looks_like_hidden_column` detecta cuando
  varios bloques "centrados" (los que quedan fuera de la columna
  izquierda/derecha detectada) están alineados entre sí y son angostos
  como una columna — señal de que hay una columna del medio que la
  heurística no reconoció como tal — y en ese caso toda la página cae a
  `order_single_column` en vez de producir un orden de 2 columnas
  incorrecto pero con apariencia de válido. Verificado con el fixture 03
  (3 columnas reales): cae al fallback y el test
  `tests/extraction/test_reading_order_three_column_limitation.py` fija
  ese comportamiento como regresión, no como bug silencioso. Si se agrega
  soporte a 3+ columnas en el futuro, ese test debe actualizarse.
- Validado contra el fixture 02 (2 columnas limpias, LaTeX): el orden
  resultante es título -> autor -> fecha -> columna izquierda completa ->
  columna derecha completa -> número de página, exactamente el orden de
  lectura humano esperado. Test en
  `tests/extraction/test_reading_order_two_column.py`. Ruff y Pyright
  estricto limpios (14 tests en total).
- Pendiente, reportado por `/code-review` sobre el trabajo del Paso 4 y
  todavía sin resolver: (1) bbox se extrae en coordenadas sin rotación
  pero `Page.width/height` sí refleja `/Rotate` — inconsistente en
  páginas rotadas; (2) `get_text("blocks")` se llama sin
  `TEXT_PRESERVE_IMAGES`, así que `BlockType.IMAGE` es código muerto y las
  imágenes embebidas desaparecen de la extracción; (3) cada página se
  procesa dos veces (`get_text("blocks")` y `get_text("text")` solo para
  `requires_ocr`), trabajo duplicado evitable. (1) y (2) son bugs de
  correctness reales, no solo eficiencia — quedan para la próxima sesión.

## Decisiones de arquitectura diferidas

- **OCR real**: se difiere completamente. Fase 1 solo detecta y marca
  `requires_ocr=True` en páginas sin texto extraíble; no se integra ningún
  motor de OCR (Tesseract, cloud OCR, etc.) todavía.
- **Capa de plantillas (ancla de texto → valor)**: producto futuro sobre
  este motor. No se diseña su API todavía; se espera que consuma la salida
  de `extraction`/`classification` tal como queda definida en Fase 1, pero
  el contrato final se revisa cuando se construya esa fase.
- **Visor móvil**: consume la función de render (bbox → recorte de
  imagen). No se construye ninguna UI ni capa de interacción en este
  módulo.
- **Clasificación de tablas con ML**: Fase 1 usa solo alineación de
  columnas. Si la heurística resulta insuficiente en PDFs reales, se
  documenta como limitación conocida en vez de introducir ML o LLM.
