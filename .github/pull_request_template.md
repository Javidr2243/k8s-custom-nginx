## Qué cambia

<!-- Resumen breve. -->

## Si el PR cambia datos (`data/`)

- [ ] Revisé la sección **⚠️ Fuente modificada** (si aparece): el cambio en el documento oficial es legítimo.
- [ ] Revisé las **anomalías** marcadas (cambios de más de ±30 % contra el periodo anterior) contra el documento original.
- [ ] Abrí al menos un documento fuente de cada municipio y comparé el total con el que muestra el resumen.
- [ ] Ningún valor faltante se rellenó ni se estimó: aparece como `null` con su `motivo`.
- [ ] No se publican datos personales (RFC de personas físicas, beneficiarios de apoyos).

## Si el PR cambia código o infraestructura

- [ ] `make lint test` pasa localmente.
- [ ] No hay `{@html}`, `innerHTML` ni recursos de terceros nuevos.
- [ ] Las acciones nuevas de GitHub están fijadas a un SHA de commit.
