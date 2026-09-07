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
