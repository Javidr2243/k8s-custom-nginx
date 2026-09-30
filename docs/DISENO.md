# Principios de diseño

Guía corta para que todas las vistas se vean y se lean igual. Sale de revisar sitios públicos y privados reconocidos por
su claridad (guía ciudadana del Tesoro de EE. UU., USAspending, GOV.UK, presupuesto de Boston, Data USA, Our World in
Data, Presupuesto Abierto de Chile, Stripe, Wise, Nubank) y de las Human Interface Guidelines de Apple (tipografía,
layout, color, gráficas, escritura y accesibilidad).

## 1. Una idea por sección

- Cada sección responde **una pregunta**. Estructura fija: etiqueta pequeña en mayúsculas (`.eyebrow`, la pregunta) →
  titular con **el hallazgo en cifras** → una línea de detalle → la gráfica → una línea de fuente.
- El titular dice lo que la gráfica muestra, con valores reales y sin adjetivos subjetivos («Dos rubros se llevan $54 de
  cada $100», no «el gasto está muy concentrado»). Se calcula de los mismos datos que la gráfica.
- Al inicio, **una oración con un número** y su contexto en gris (`.titular` + `.suave`), y una fila abierta de cifras
  clave (`.cifras`, con `StatTile` dentro).
- **Nada se repite**: si un bloque repite el titular de otro o no cambia entre periodos, se quita o se resume en
  una línea (con el detalle plegado). Antes de quitar algo se comprueba que su cifra siga en otro lugar.
- Menú corto (7 entradas) ordenado por utilidad; páginas de consulta (Movimientos, Fuentes) en el pie y en enlaces
  en contexto.
- Componente `Seccion` (`pregunta`, `titular`, `detalle`, `banda`) para no repetir la estructura en cada vista; `.dos`
  pone dos secciones lado a lado dentro de una banda.

## 2. Espacio en lugar de cajas

- Las secciones se separan con **bandas de fondo a todo el ancho** (`.banda`) y líneas finas, no con tarjetas.
- Las tarjetas se reservan para elementos que se comparan entre sí (p. ej. las revisiones en «Fuentes»).
- Listas de enlaces al estilo GOV.UK: título, una línea de descripción y una flecha.

## 3. Tipografía

- Una sola familia: **Inter** (variable, alojada en el propio sitio por la CSP), con tamaño óptico automático.
- Pesos 400–750; nunca pesos finos. Cifras con `tabular-nums` (`.num`) para que se alineen.
- Jerarquía por tamaño y peso: h1 2.6 rem, titulares de sección 1.6 rem, texto 1 rem, notas 0.875 rem (mínimo).
- Unidades largas en tamaño menor junto al número («$1,457.0 <small>millones</small>») para que no salten de línea.
- Titulares con `text-wrap: balance`; párrafos con `text-wrap: pretty`; líneas de 60–80 caracteres.

## 4. Color

- El color identifica **una sola cosa** en todo el sitio: cada municipio tiene el suyo; las magnitudes usan una sola
  rampa azul; el estado (bien / atención) usa verde y ámbar con icono y texto, nunca solo color.
- Paleta validada para daltonismo; modo oscuro con sus propios tonos. Contraste mínimo 4.5:1 en texto.

## 5. Fuentes sin ruido

- Toda cifra tiene fuente, pero se muestra como **una línea discreta** («Fuente: título… · Detalles»); los detalles
  (copia archivada, fechas, huella SHA-256) se abren a petición. Revelación progresiva de máximo dos niveles.
- Fecha de los datos visible arriba de la página.

## 6. Accesibilidad y uso en teléfono

- Ninguna información crítica depende de pasar el cursor: lo que muestra un tooltip también está en la leyenda o en
  «Ver como tabla».
- Objetivos táctiles de 44 px; áreas de toque más grandes que la marca en las gráficas.
- Cada gráfica tiene descripción para lectores de pantalla y tabla alternativa. La tabla no repite la gráfica: trae
  los mismos datos **más al menos una columna que la gráfica no muestra** (% del total, % de su presupuesto, cambio
  respecto al periodo anterior). Donde la gráfica ya rotula cada monto (Sankey), se reemplaza por una comparación con
  el año anterior.
- Se prueba a 390 px de ancho, en claro y oscuro, sin desplazamiento horizontal.
