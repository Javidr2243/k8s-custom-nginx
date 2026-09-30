# Política de seguridad

## Reportar una vulnerabilidad o un error en los datos

Si encuentras una vulnerabilidad en el sitio o en la infraestructura, **no abras un issue público**.
Usa el reporte privado de GitHub: pestaña **Security → Report a vulnerability** de este repositorio.

Si encuentras un **número incorrecto** (distinto al documento oficial), abre un issue con:
el municipio, el periodo, el valor que muestra el sitio, el valor del documento oficial y el enlace a ese documento.

Respondemos en un plazo de 7 días.

## Alcance

- El sitio es estático: no tiene cuentas de usuario, formularios, cookies ni base de datos.
- Dentro del alcance: el contenedor (`Dockerfile`, `nginx.conf`, `security-headers.conf`),
  la configuración de despliegue (`deploy/`), los workflows de GitHub Actions y el pipeline de datos (`pipeline/`).
- Fuera del alcance: los sitios de los gobiernos de donde vienen los datos.

## Medidas actuales

Ver la sección "Seguridad" del README.
