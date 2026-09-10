import { Pipe, PipeTransform } from '@angular/core';

/**
 * Fechas en la zona horaria del semillero.
 *
 * El backend guarda todo en UTC y la interfaz lo presenta en `America/Bogota`
 * (RNF-06). Se usa `Intl` y no el `DatePipe` de Angular porque el parámetro de
 * zona de ese último espera un desplazamiento fijo, y Colombia se nombra mejor
 * por su identificador que por «-0500».
 */
export type BogotaDateFormat = 'date' | 'datetime';

/**
 * Una fecha sin hora: `due_date`, `start_date`, cualquier `datetime.date` del
 * backend. No es un instante sino un día del calendario, y hay que tratarla
 * como tal (ver `transform`).
 */
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

const FORMATS: Record<BogotaDateFormat, Intl.DateTimeFormatOptions> = {
  date: { day: '2-digit', month: 'short', year: 'numeric' },
  datetime: {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
};

@Pipe({ name: 'bogotaDate' })
export class BogotaDatePipe implements PipeTransform {
  transform(value: string | null | undefined, format: BogotaDateFormat = 'date'): string {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '—';

    // Una fecha sin hora es un día del calendario, no un instante, y no se
    // convierte de zona: el 31 de julio es el 31 de julio. `new Date` la
    // interpreta como medianoche UTC, así que pasarla por `America/Bogota`
    // (−5) la echaba cinco horas atrás y mostraba el día anterior. Todo
    // vencimiento del producto se veía un día antes de lo que era.
    if (DATE_ONLY.test(value)) {
      return new Intl.DateTimeFormat('es-CO', {
        ...FORMATS.date,
        timeZone: 'UTC',
      }).format(parsed);
    }

    return new Intl.DateTimeFormat('es-CO', {
      ...FORMATS[format],
      timeZone: 'America/Bogota',
    }).format(parsed);
  }
}
