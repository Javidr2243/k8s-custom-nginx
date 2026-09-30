# ¿A dónde va tu dinero? MTY

Aplicación web ciudadana que explica, en lenguaje sencillo, cómo obtienen y gastan su dinero los gobiernos
municipales de **Monterrey**, **San Pedro Garza García** y **Santa Catarina** (Nuevo León): de dónde viene el
dinero, quién lo gasta, en qué, qué cambió en el último trimestre, cuánto deben y a quién le compran.

> **Sitio independiente, no oficial.** Todas las cifras vienen de documentos oficiales y cada una enlaza a su
> fuente. **Nunca se inventan, estiman ni rellenan números:** lo que falta se marca como faltante y se explica por
> qué. Montos en **pesos mexicanos nominales** (sin ajustar por inflación).

## Qué muestra

| Sección | Qué responde |
|---|---|
| **Inicio** | Cuánto gastó el municipio en el periodo, «de cada $100», quién gasta más y los movimientos recientes |
| **Mapa del gobierno** | Grafo radial: de dónde viene el dinero → gobierno → dependencias (Monterrey) o tipos de gasto. Tamaño por aprobado o gastado. Panel con aprobado vs. modificado vs. devengado, tendencia trimestral, desglose, cambios a mitad de año y fuentes |
| **Flujo del dinero** | Diagrama Sankey anual: impuestos, participaciones, aportaciones y préstamos → capítulos del gasto |
| **Comparar** | Los tres municipios por habitante (último trimestre común y serie anual 2018–2025) |
| **Deuda** | Saldo trimestral, pagos, intereses (Monterrey), créditos vigentes y calificación del Sistema de Alertas |
| **Contratos** | Contratos y proveedores: tipo de procedimiento, concentración, tabla con búsqueda y descarga CSV |
| **Movimientos** | Nuevos reportes, cambios grandes al presupuesto, deuda y contratos grandes |
| **Glosario / Acerca de** | Más de 50 términos en lenguaje sencillo; método, límites, faltantes, privacidad y todas las fuentes |

Funciona en celulares, en modo claro y oscuro, con teclado y lector de pantalla (cada gráfica tiene una tabla).

## Fuentes de datos

Todas están declaradas, una por una, en [`pipeline/sources.yaml`](pipeline/sources.yaml) (URL, emisor, página de
origen y periodo). Los originales se guardan en [`data/raw/`](data/raw/) con su huella SHA-256 en
[`data/raw/manifest.json`](data/raw/manifest.json).

| Fuente | Emisor | Formato | Cobertura | Detalle |
|---|---|---|---|---|
| Estados analíticos de ingresos y del ejercicio del presupuesto de egresos ([Información fiscal](https://www.monterrey.gob.mx/transparencia/Oficial_/Informacion_Fiscal/)) | Municipio de Monterrey, Tesorería | XLSX trimestral | 1T 2023 – 2T 2026 | Por dependencia (19), por capítulo y concepto, ingresos por rubro |
| Formato NLA95FXXIIB «Ejercicio de los egresos presupuestarios» (Ley de Transparencia NL, art. 95 fr. XXII-B) | San Pedro Garza García; Santa Catarina | XLSX trimestral | 2023 – 2T 2026 (con faltantes) | Por capítulo del gasto |
| Formato NLA95FXXIX «Resultados de adjudicaciones, invitaciones y licitaciones» | Monterrey; Santa Catarina | XLS/XLSX | 2025 – jul 2026 | Un renglón por contrato |
| Relación de contratos de adquisiciones 2024–2027 ([licitaciones.sanpedro.gob.mx](https://licitaciones.sanpedro.gob.mx/)) | San Pedro Garza García | XLSX | 2024 – 2026 | Un renglón por contrato |
| Deuda pública total (amortización e intereses) | Municipio de Monterrey | XLSX | 2014 – 2026 | Anual |
| [EFIPEM](https://www.inegi.org.mx/programas/finanzas/) — finanzas públicas municipales | INEGI | CSV (ZIP de 96 MB; se guarda un extracto) | 2018 – 2025 (2025 preliminar) | Ingresos y egresos por capítulo, mismo formato para los tres |
| Marco Geoestadístico (población del Censo 2020) | INEGI | JSON | 2020 | Población por municipio |
| [Registro Público Único](https://www.disciplinafinanciera.hacienda.gob.mx/) — saldos por municipio y registro de créditos | SHCP | XLSX | 1T 2023 – 2T 2026; diario | Saldo por tipo de acreedor; un renglón por crédito |
| [Sistema de Alertas](https://www.disciplinafinanciera.hacienda.gob.mx/es/DISCIPLINA_FINANCIERA/Sistema_de_Alertas) | SHCP | XLSX | 2023 – 1S 2026 | Resultado e indicadores por municipio |

## Límites de los datos

- **San Pedro y Santa Catarina** publican el gasto por dependencia y los ingresos trimestrales **solo en PDF
  escaneado**; aquí se muestra su gasto por capítulo y sus ingresos anuales del INEGI. No se usa OCR.
- **Faltantes** (se muestran en el sitio con su motivo): San Pedro 3T 2023, 3T y 4T 2024 y 3T 2025 (el formato se
  publicó sin cifras o no se publicó); Santa Catarina 2023 completo (el documento repite las mismas cifras en los
  cuatro trimestres), 3T 2024 y 1T 2026 (solo PDF escaneado).
- Los **organismos paramunicipales y fideicomisos** no aparecen en los reportes principales de los municipios.
- Las cifras del **INEGI 2025 son preliminares**. «Gasto» en la comparación = total de egresos menos disponibilidad
  final (efectivo en caja, que no es gasto).
- **Deuda:** solo la inscrita en el Registro Público Único. Los créditos ya liquidados salen del registro.
- **Contratos:** Monterrey reserva el nombre del proveedor en varios contratos; San Pedro publica solo
  adquisiciones (no obra pública); en Santa Catarina solo se encontraron invitaciones y licitaciones.
- Algunos documentos oficiales tienen **inconsistencias internas** (p. ej. un «modificado» que no es aprobado +
  ampliaciones). Se publican tal cual y se registran en el reporte de validación.

## Cómo se actualizan los datos

**Automático (recomendado):** cada lunes el workflow [`refresh-data.yml`](.github/workflows/refresh-data.yml)
busca trimestres nuevos, descarga, valida, reconstruye y, si algo cambió, **abre un PR** con un resumen:
documentos nuevos, **⚠️ fuentes modificadas** (archivos ya descargados que cambiaron en el sitio oficial), cambios
de más de ±30 %, advertencias y lo que hay que revisar a mano. Nada se publica hasta que una persona aprueba el PR
y luego el despliegue a producción. Los municipios suelen publicar el trimestre ~1 mes después del cierre
(abril, julio, octubre y enero/febrero).

> Los PR creados por el workflow no disparan la CI por sí solos (limitación de GitHub con `GITHUB_TOKEN`); el
> workflow ya corre toda la validación antes de abrirlo. Para que la CI corra en el PR, ciérralo y vuelve a
> abrirlo.

**Manual:**

```sh
make data     # discover + fetch + build-data
make test     # pruebas (incluye totales verificados contra los documentos)
git diff data # revisa los cambios y abre un PR
```

Para agregar un documento que `discover` no encuentra solo (Santa Catarina, contratos de San Pedro), agrega una
entrada en `pipeline/sources.yaml` copiando una existente del mismo `tipo`, y corre `make fetch build-data`.

## Correr localmente

Requisitos: Node 22, [uv](https://docs.astral.sh/uv/) y Docker.

```sh
make install        # dependencias desde los lockfiles
make lint test      # linters, tipos y pruebas
make dev            # sitio en http://localhost:5173 (lee data/public/v1)
make image run      # contenedor endurecido, como en producción, en http://localhost:8080
make check-headers  # revisa las cabeceras de seguridad del contenedor
make e2e            # pruebas en navegador contra el contenedor
```

## Arquitectura

```
pipeline/   Python 3.12: descarga → valida → JSON estático (sin servidor, sin base de datos)
  sources.yaml, gdmty/{fetch,safeio,discover,build,validate}.py, gdmty/parsers/*
data/raw/   originales oficiales + manifest.json (SHA-256, fechas, historial)
data/public/v1/  JSON que carga el sitio + SHA256SUMS
web/        Svelte 5 + Vite + TypeScript; gráficas en SVG con módulos de d3
Dockerfile, nginx.conf, security-headers.conf   nginx sin privilegios, solo archivos estáticos
deploy/     Caddy (HTTPS) + docker compose + despliegue firmado para un VPS → ver deploy/README.md
```

**Por qué así:** el sitio es estático (no hay API, base de datos, cuentas ni formularios), lo que casi elimina la
superficie de ataque y lo hace rápido y barato. El procesamiento corre en GitHub Actions o localmente, nunca en el
servidor. Svelte compila a paquetes pequeños (77 KB gzip) y escapa el texto por defecto; las gráficas son SVG
escritas a mano con módulos de d3 (sin librerías pesadas), con disposición radial fija en lugar de un grafo de
fuerzas, que en celular se vuelve ilegible.

## Seguridad

- **Sitio:** CSP estricta (`default-src 'none'`, sin scripts ni estilos en línea, sin terceros), HSTS,
  `nosniff`, `frame-ancestors 'none'`, solo GET/HEAD, límite de peticiones por cliente; sin cookies ni analítica.
  `{@html}` e `innerHTML` están prohibidos por lint. CSV exportado protegido contra inyección de fórmulas.
- **Contenedor:** nginx sin privilegios fijado por digest, sistema de archivos de solo lectura, sin capacidades,
  `no-new-privileges`, límites de memoria y procesos.
- **Pipeline (archivos no confiables):** solo HTTPS a dominios en lista blanca (revisada en cada redirección), TLS
  siempre verificado (certificados intermedios en `pipeline/certs/`), límites de tamaño, tipo por *magic bytes*,
  ZIP sin rutas peligrosas ni bombas; RFC de personas físicas enmascarado.
- **CI/CD:** acciones fijadas a SHA, permisos mínimos por job, lockfiles, Dependabot, zizmor, actionlint,
  gitleaks, pip-audit, npm audit, Trivy, pruebas en navegador con cero violaciones de CSP. La imagen publicada es
  exactamente la probada, **firmada con cosign** (keyless), con SBOM y procedencia; el VPS verifica la firma antes
  de desplegar y regresa a la versión anterior si falla el healthcheck.
- Reporte de vulnerabilidades: ver [SECURITY.md](SECURITY.md).

## Despliegue

Guía paso a paso (endurecimiento del VPS, DNS, GitHub, primer despliegue y reversión): [deploy/README.md](deploy/README.md).

## Licencia

Código: MIT. Los datos pertenecen a sus emisores (municipios, INEGI, SHCP) y deben citarse; ver `LICENSE`.
