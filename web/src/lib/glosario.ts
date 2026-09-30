// Plain-language glossary. Used by the <Termino> component (pop-up explanation) and the /glosario page.
// Content is authored here, never taken from external data.

export interface Entrada {
  termino: string;
  corto: string; // one or two sentences for the pop-up
  largo?: string; // extra detail for the glossary page
  ver?: string[];
}

export const GLOSARIO: Record<string, Entrada> = {
  presupuesto: {
    termino: 'Presupuesto de egresos',
    corto: 'El plan de gasto del municipio para el año: cuánto piensa gastar y en qué. Lo aprueba el Ayuntamiento (cabildo).',
    ver: ['aprobado', 'modificado'],
  },
  aprobado: {
    termino: 'Aprobado',
    corto: 'Lo que el Ayuntamiento autorizó gastar al inicio del año, antes de cualquier cambio.',
    ver: ['modificado', 'ampliaciones'],
  },
  ampliaciones: {
    termino: 'Ampliaciones y reducciones',
    corto: 'Cambios al presupuesto durante el año: dinero que se agrega (ampliación) o se quita (reducción) a un área o rubro.',
    largo: 'Son normales: por ejemplo, cuando llegan ingresos que no se esperaban o cuando se mueve dinero de un área a otra. Si son muy grandes, conviene preguntar por qué.',
  },
  modificado: {
    termino: 'Modificado',
    corto: 'El presupuesto vigente después de los cambios: Aprobado + Ampliaciones − Reducciones.',
  },
  devengado: {
    termino: 'Devengado',
    corto: 'Gasto ya comprometido de forma definitiva: el bien se recibió o el servicio se prestó, aunque todavía no se haya pagado. Es la mejor medida de "cuánto se gastó".',
    ver: ['pagado', 'ejercido'],
  },
  ejercido: {
    termino: 'Ejercido',
    corto: 'Gasto que ya tiene autorizado su pago (cuenta por liquidar certificada). Está entre "devengado" y "pagado".',
  },
  pagado: {
    termino: 'Pagado',
    corto: 'Dinero que ya salió de la tesorería: el pago efectivamente realizado.',
  },
  subejercicio: {
    termino: 'Subejercicio',
    corto: 'La parte del presupuesto modificado que todavía no se ha gastado (Modificado − Devengado). A mitad de año es normal que sea grande.',
  },
  'solicitud-informacion': {
    termino: 'Solicitud de acceso a la información',
    corto: 'Pregunta por escrito que cualquier persona puede hacer a un gobierno, sin dar motivos ni identificarse con documentos. Es gratuita y deben responder en un plazo de 20 días hábiles (ampliable).',
    largo: 'Se presenta en la Plataforma Nacional de Transparencia o en la unidad de transparencia del municipio. Si la respuesta no te convence, puedes presentar un recurso de revisión.',
  },
  acumulado: {
    termino: 'Cifras acumuladas',
    corto: 'Los reportes trimestrales suman desde el 1 de enero hasta la fecha de corte. El 2º trimestre incluye enero a junio, no solo abril a junio.',
  },
  nominales: {
    termino: 'Pesos nominales',
    corto: 'Pesos tal como se reportaron en cada año, sin ajustar por inflación. Comparar años distintos exagera un poco el crecimiento.',
  },
  capitulo: {
    termino: 'Capítulo del gasto',
    corto: 'La clasificación oficial de en qué se gasta (CONAC): sueldos, materiales, servicios, apoyos, equipo, obra pública, deuda, etc.',
    largo: 'Capítulo 1000 Servicios personales · 2000 Materiales y suministros · 3000 Servicios generales · 4000 Transferencias, subsidios y ayudas · 5000 Bienes muebles e inmuebles · 6000 Inversión pública (obra) · 7000 Inversiones financieras y provisiones · 8000 Participaciones y aportaciones · 9000 Deuda pública.',
  },
  'cap-1000': { termino: 'Servicios personales (1000)', corto: 'Sueldos, prestaciones, aguinaldos y seguridad social del personal del municipio, incluida la policía.' },
  'cap-2000': { termino: 'Materiales y suministros (2000)', corto: 'Compras que se consumen: combustible, papelería, uniformes, medicinas, materiales de construcción y reparación.' },
  'cap-3000': { termino: 'Servicios generales (3000)', corto: 'Servicios que el municipio contrata: electricidad (incluido el alumbrado público), recolección de basura, rentas, mantenimiento, comunicación.' },
  'cap-4000': { termino: 'Transferencias y apoyos (4000)', corto: 'Dinero que se entrega a otros: apoyos sociales, becas, subsidios, pensiones y transferencias a organismos como el DIF.' },
  'cap-5000': { termino: 'Bienes muebles e inmuebles (5000)', corto: 'Compra de equipo y bienes duraderos: patrullas, vehículos, computadoras, mobiliario, terrenos.' },
  'cap-6000': { termino: 'Inversión pública (6000)', corto: 'Obra pública: calles, banquetas, puentes, drenaje pluvial, parques, edificios públicos.' },
  'cap-7000': { termino: 'Inversiones financieras y provisiones (7000)', corto: 'Reservas para contingencias e inversiones financieras.' },
  'cap-8000': { termino: 'Participaciones y aportaciones (8000)', corto: 'Recursos que se transfieren a otros órdenes de gobierno. En municipios suele ser cero.' },
  'cap-9000': { termino: 'Deuda pública (9000)', corto: 'Pago de la deuda: capital (amortización), intereses y comisiones.' },
  dependencia: {
    termino: 'Dependencia',
    corto: 'Cada secretaría u oficina del gobierno municipal (por ejemplo, Seguridad, Obras Públicas, Servicios Públicos). Es "quién gasta".',
  },
  paramunicipal: {
    termino: 'Organismo paramunicipal',
    corto: 'Institución con presupuesto propio creada por el municipio (por ejemplo, un instituto de la mujer o de planeación). Sus cuentas no siempre aparecen en los reportes principales.',
  },
  fideicomiso: {
    termino: 'Fideicomiso',
    corto: 'Un fondo que se entrega a un banco para que lo administre con un fin específico. Sus recursos pueden quedar fuera del presupuesto principal.',
  },
  ingresos: {
    termino: 'Ingresos',
    corto: 'Todo el dinero que recibe el municipio: impuestos locales, derechos, dinero federal (participaciones y aportaciones) y préstamos.',
  },
  impuestos: {
    termino: 'Impuestos',
    corto: 'Lo que cobra el municipio por ley, principalmente el predial y el impuesto sobre adquisición de inmuebles (ISAI).',
  },
  predial: {
    termino: 'Impuesto predial',
    corto: 'Impuesto anual que pagan los dueños de casas, terrenos y locales. Es el principal ingreso propio de los municipios.',
  },
  derechos: {
    termino: 'Derechos',
    corto: 'Cobros por servicios o permisos del municipio: licencias de construcción, alumbrado, panteones, trámites.',
  },
  productos: { termino: 'Productos', corto: 'Ingresos por usar o vender bienes del municipio: rentas de locales, intereses bancarios.' },
  aprovechamientos: { termino: 'Aprovechamientos', corto: 'Otros ingresos no fiscales, como multas de tránsito, recargos e indemnizaciones.' },
  'ingresos-propios': {
    termino: 'Ingresos propios',
    corto: 'Lo que el municipio cobra por su cuenta: impuestos como el predial, derechos (licencias, permisos), productos y aprovechamientos (multas, recargos).',
    largo: 'Frente a ellos están las participaciones y aportaciones que envía la federación. Cuanto mayor la parte propia, menos depende el municipio de esas transferencias.',
    ver: ['participaciones', 'aportaciones'],
  },
  participaciones: {
    termino: 'Participaciones',
    corto: 'La parte de los impuestos federales (IVA, ISR, etc.) que le toca al municipio por ley. Llegan a través del estado y se pueden gastar libremente.',
    ver: ['aportaciones'],
  },
  aportaciones: {
    termino: 'Aportaciones (Ramo 33)',
    corto: 'Dinero federal con destino fijo: sólo puede usarse para lo que dice la ley (por ejemplo, infraestructura social o seguridad).',
    ver: ['fortamun', 'fism'],
  },
  fortamun: {
    termino: 'FORTAMUN',
    corto: 'Fondo federal para el fortalecimiento de los municipios. Se usa sobre todo en seguridad pública y en pagar obligaciones financieras.',
  },
  fism: {
    termino: 'FISM',
    corto: 'Fondo federal de infraestructura social municipal: obras para zonas con más pobreza (agua, drenaje, calles, centros comunitarios).',
  },
  financiamiento: {
    termino: 'Financiamiento',
    corto: 'Dinero que entra por préstamos (deuda). No es un ingreso "ganado": se tiene que pagar con intereses.',
  },
  'ingresos-libre-disposicion': {
    termino: 'Ingresos de libre disposición',
    corto: 'Ingresos que el municipio puede usar en lo que decida: ingresos propios más participaciones federales.',
  },
  'disponibilidad-final': {
    termino: 'Disponibilidad final',
    corto: 'El efectivo que le queda al municipio en caja al cerrar el año. No es gasto, por eso se resta al comparar.',
  },
  deuda: {
    termino: 'Deuda pública',
    corto: 'Préstamos que el municipio debe a bancos. Se registran ante la Secretaría de Hacienda en el Registro Público Único.',
  },
  saldo: { termino: 'Saldo de la deuda', corto: 'Lo que falta por pagar de los préstamos en una fecha.' },
  amortizacion: { termino: 'Amortización', corto: 'Pago del capital del préstamo; reduce el saldo de la deuda.' },
  intereses: { termino: 'Intereses', corto: 'El costo de pedir prestado: lo que se paga al banco además del capital.' },
  tiie: {
    termino: 'TIIE',
    corto: 'Tasa de interés de referencia en México. Los créditos municipales suelen cobrar TIIE más una "sobretasa".',
  },
  rpu: {
    termino: 'Registro Público Único (RPU)',
    corto: 'Registro de la Secretaría de Hacienda donde deben inscribirse todos los préstamos de estados y municipios.',
  },
  alertas: {
    termino: 'Sistema de Alertas',
    corto: 'Calificación de Hacienda sobre qué tan manejable es la deuda de un municipio: sostenible, en observación o elevado.',
    largo: 'Usa tres indicadores: deuda entre ingresos de libre disposición, pago de deuda entre esos mismos ingresos, y obligaciones de corto plazo (menos efectivo) entre ingresos totales.',
  },
  'adjudicacion-directa': {
    termino: 'Adjudicación directa',
    corto: 'El gobierno elige al proveedor sin concurso abierto. La ley la permite en montos bajos o casos de excepción; conviene revisar que esté justificada.',
  },
  'invitacion-restringida': {
    termino: 'Invitación restringida',
    corto: 'El gobierno invita a por lo menos tres proveedores a presentar propuestas. Hay competencia, pero no está abierta a todos.',
  },
  licitacion: {
    termino: 'Licitación pública',
    corto: 'Concurso abierto: cualquier empresa que cumpla los requisitos puede participar. Es la forma más competitiva de comprar.',
  },
  'convenio-modificatorio': {
    termino: 'Convenio modificatorio',
    corto: 'Cambio a un contrato ya firmado: más monto, más tiempo o más productos.',
  },
  concentracion: {
    termino: 'Concentración de proveedores',
    corto: 'Qué parte del dinero contratado se va a los 10 proveedores más grandes. Una concentración muy alta puede indicar poca competencia.',
  },
  rfc: {
    termino: 'RFC',
    corto: 'Registro Federal de Contribuyentes. Aquí solo se muestra el de empresas; el de personas físicas se oculta para proteger datos personales.',
    largo: 'En el RFC de una empresa (12 caracteres), los 6 números después de las 3 letras son su fecha de constitución: año, mes y día.',
  },
  'area-solicitante': {
    termino: 'Área solicitante',
    corto: 'La oficina que necesitaba la compra. Puede ser distinta del área contratante, que organiza el concurso (a menudo una oficina central de compras).',
  },
  reservada: {
    termino: 'Información reservada',
    corto: 'Datos que el municipio decidió no publicar invocando la ley de transparencia (por ejemplo, por seguridad). Se muestran tal cual, sin adivinar.',
  },
  'por-habitante': {
    termino: 'Por habitante',
    corto: 'El monto dividido entre la población del municipio (Censo 2020). Sirve para comparar municipios de distinto tamaño.',
  },
  efipem: {
    termino: 'EFIPEM (INEGI)',
    corto: 'Estadística anual del INEGI con ingresos y gastos de todos los municipios en el mismo formato. Permite comparar, pero se publica con meses de retraso.',
  },
  sipot: {
    termino: 'SIPOT',
    corto: 'Formatos oficiales de transparencia que todos los gobiernos deben llenar y publicar (por ejemplo, el ejercicio del presupuesto o los contratos).',
  },
  'cuenta-publica': {
    termino: 'Cuenta Pública',
    corto: 'El informe anual oficial de cómo se usaron los recursos. La revisa la Auditoría Superior del Estado.',
  },
  sha256: {
    termino: 'Huella SHA-256',
    corto: 'Un código único calculado a partir del contenido de un archivo. Si el archivo cambia aunque sea un poco, la huella cambia; sirve para comprobar que una copia es idéntica al original.',
  },
  'copia-archivada': {
    termino: 'Copia archivada',
    corto: 'El archivo oficial exacto que se usó para calcular las cifras, guardado por este sitio por si el enlace del gobierno cambia o desaparece.',
  },
  trimestre: {
    termino: 'Trimestre',
    corto: 'Periodo de tres meses. Los municipios reportan su avance financiero cada trimestre (marzo, junio, septiembre y diciembre).',
  },
};

export function entrada(id: string): Entrada | undefined {
  return GLOSARIO[id];
}
