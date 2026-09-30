// CONAC spending chapters with a plain-language name (same keys as the pipeline).
export const CAPITULOS: Record<string, { nombre: string; sencillo: string; glosario: string }> = {
  '1000': { nombre: 'Servicios personales', sencillo: 'Sueldos y prestaciones', glosario: 'cap-1000' },
  '2000': { nombre: 'Materiales y suministros', sencillo: 'Materiales y combustible', glosario: 'cap-2000' },
  '3000': { nombre: 'Servicios generales', sencillo: 'Servicios (luz, limpia, rentas…)', glosario: 'cap-3000' },
  '4000': { nombre: 'Transferencias, asignaciones, subsidios y otras ayudas', sencillo: 'Apoyos y subsidios', glosario: 'cap-4000' },
  '5000': { nombre: 'Bienes muebles, inmuebles e intangibles', sencillo: 'Equipo, vehículos y bienes', glosario: 'cap-5000' },
  '6000': { nombre: 'Inversión pública', sencillo: 'Obra pública', glosario: 'cap-6000' },
  '7000': { nombre: 'Inversiones financieras y otras provisiones', sencillo: 'Reservas e inversiones', glosario: 'cap-7000' },
  '8000': { nombre: 'Participaciones y aportaciones', sencillo: 'Transferencias a otros gobiernos', glosario: 'cap-8000' },
  '9000': { nombre: 'Deuda pública', sencillo: 'Pago de deuda', glosario: 'cap-9000' },
};

export function sencillo(clave: string): string {
  return CAPITULOS[clave]?.sencillo ?? clave;
}
