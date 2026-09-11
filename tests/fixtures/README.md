# Fixtures de prueba (PDFs reales)

PDFs reales tomados de repositorios open-source usados como suites de
regresión por proyectos de referencia en parsing de PDF (`pdfplumber`,
`camelot`, `ocrmypdf`, `py-pdf/sample-files`). Se eligieron documentos
reales generados por herramientas o publicados por entidades de gobierno,
no fixtures sintéticas — cada uno rompe las heurísticas de forma distinta,
que es justamente lo que necesitamos documentar como límite conocido si no
se resuelve en Fase 1.

Ningún documento es del dominio marítimo/aduanero propio del proyecto
(facturas, manifiestos, B/L); son la mejor aproximación pública disponible
para cada caso de layout. Si más adelante conseguimos documentos reales
del dominio (facturas o B/L propios, anonimizados), deberían sumarse aquí
sin reemplazar estos — cubren casos de layout que quizás esos documentos
no cubran igual de bien.

| Archivo | Caso que cubre | Páginas | Fuente | Licencia |
|---|---|---|---|---|
| `01_single_column_pdflatex.pdf` | 1 columna (caso base) | 4 | [py-pdf/sample-files](https://github.com/py-pdf/sample-files) — `004-pdflatex-4-pages` | CC-BY-SA-4.0 |
| `02_two_column_pdflatex.pdf` | 2 columnas | 3 | [py-pdf/sample-files](https://github.com/py-pdf/sample-files) — `026-latex-multicolumn` | CC-BY-SA-4.0 |
| `03_federal_register_3col_header_footer.pdf` | 3 columnas **+** header/footer repetido — caso límite fuera de alcance (Fase 1 solo cubre 1 y 2 columnas) | 15 | [jsvine/pdfplumber](https://github.com/jsvine/pdfplumber) tests/pdfs — publicación real del *US Federal Register* (regla propuesta FAA, 2020) | Documento del gobierno de EE.UU., dominio público (17 U.S.C. §105) |
| `04_table_india_budget.pdf` | Tabla (alineación de columnas numéricas) | 1 | [camelot-dev/camelot](https://github.com/camelot-dev/camelot) tests/files `budget.pdf` — resumen del presupuesto del gobierno de India 2014-2015 | Documento de gobierno, redistribuido como fixture de test en el repo de Camelot (MIT) |
| `05_table_warn_layoff_report.pdf` | Tabla multi-página (filas que continúan entre páginas) | 16 | [jsvine/pdfplumber](https://github.com/jsvine/pdfplumber) tests/pdfs — reporte WARN (avisos de despido masivo) de California | Documento de gobierno estatal (CA), dominio público |
| `06_scanned_multipage.pdf` | Escaneado, sin texto extraíble, multi-página | 6 | [ocrmypdf/OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) tests/resources `multipage.pdf` | MIT (fixture de test de OCRmyPDF) |
| `07_scanned_single_page.pdf` | Escaneado, sin texto extraíble, 1 página, fuentes/ilustraciones difíciles | 1 | [ocrmypdf/OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) tests/resources `c03-29.pdf` — página de *Adventures of Huckleberry Finn* (Project Gutenberg) | Project Gutenberg, dominio público |

## Notas de verificación (PyMuPDF)

- `01` y `02`: confirmado `has_text=True`, distribución de palabras entre
  mitad izquierda/derecha de página consistente con 1 y 2 columnas
  respectivamente.
- `03`: header (`Federal Register / Vol. 85, No. 152 / ...`) y footer
  (`VerDate Sep<11>2014 ... jbell on DSKJLSW7X2PROD with PROPOSALS`) se
  repiten literalmente en la misma posición en todas las páginas
  verificadas (1-3). **Corrección** (encontrada al implementar la
  heurística de 2 columnas): no son 2 columnas, son 3 (x0 en 45, 222 y
  399 puntos) — el chequeo inicial por bloques de palabras
  izquierda/derecha no distingue 3 columnas de 2. Se renombró de
  `03_federal_register_2col_...` a `03_federal_register_3col_...` y pasó
  a ser el caso límite que documenta el fallback de `order_page()` en
  layouts de 3+ columnas (fuera de alcance de Fase 1), en vez del caso
  base de 2 columnas.
- `04`: tabla real de cifras presupuestarias, columnas numéricas alineadas
  verticalmente, sin líneas de tabla explícitas dibujadas (fuerza a la
  heurística de alineación en vez de detección de bordes).
- `05`: cada página continúa filas de tabla que empiezan en la página
  anterior — caso conocido difícil para "orden de lectura" y para
  "header/footer" (el texto que se repite arriba de página 2 en realidad
  es continuación de tabla, no un header real; riesgo de falso positivo).
- `06` y `07`: `has_text=False`, ambas páginas contienen exactamente 1
  imagen y cero bloques de texto extraíble — confirman el caso
  `requires_ocr=True`.
