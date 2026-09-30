# ¿A dónde va tu dinero? MTY

Aplicación web ciudadana que explica, en lenguaje sencillo, cómo obtienen y gastan su dinero los gobiernos
municipales de **Monterrey**, **San Pedro Garza García** y **Santa Catarina** (Nuevo León): de dónde viene el
dinero, quién lo gasta, en qué, qué cambió recientemente, cuánto deben y a quién le compran.

> Sitio independiente, no oficial. Todas las cifras vienen de documentos oficiales y enlazan a su fuente.
> Montos en pesos mexicanos nominales (sin ajustar por inflación).

**Estado:** en construcción (hito M0: estructura del proyecto).

## Arquitectura

```
pipeline/  Python: descarga los reportes oficiales, los valida y genera JSON  →  data/public/v1/
web/       Svelte 5 + Vite + TypeScript: sitio estático que lee ese JSON
Dockerfile + nginx.conf: nginx sin privilegios sirve el sitio (sin backend ni base de datos)
deploy/    Caddy (HTTPS) + docker compose para un VPS
```

## Desarrollo local

Requisitos: Node 22, [uv](https://docs.astral.sh/uv/), Docker.

```sh
make install      # dependencias desde lockfiles
make test lint    # pruebas y linters
make dev          # http://localhost:5173
make image run    # contenedor endurecido en http://localhost:8080
make check-headers
```

La documentación completa (fuentes de datos, cómo actualizarlos, límites de los datos, seguridad y despliegue)
se completa en el hito M9.
