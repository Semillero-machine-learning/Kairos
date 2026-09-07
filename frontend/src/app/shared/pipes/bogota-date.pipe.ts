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
    return new Intl.DateTimeFormat('es-CO', {
      ...FORMATS[format],
      timeZone: 'America/Bogota',
    }).format(parsed);
  }
}
