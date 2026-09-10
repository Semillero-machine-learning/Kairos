import { describe, expect, it } from 'vitest';

import { BogotaDatePipe } from './bogota-date.pipe';

describe('BogotaDatePipe', () => {
  const pipe = new BogotaDatePipe();

  it('presenta en America/Bogota lo que el backend guarda en UTC (RNF-06)', () => {
    // 02:30 UTC del día 7 son las 21:30 del día 6 en Colombia: la fecha cambia.
    expect(pipe.transform('2026-09-07T02:30:00Z')).toContain('06');
    expect(pipe.transform('2026-09-07T02:30:00Z', 'datetime')).toContain('09:30');
  });

  it('no mueve de día una fecha sin hora, que es un día y no un instante', () => {
    // `due_date` y `start_date` llegan como `2026-07-31`, sin hora. Es el día
    // límite, y el día límite no se convierte de zona horaria: tratarlo como
    // medianoche UTC y pasarlo a Bogotá mostraba el 30.
    expect(pipe.transform('2026-07-31')).toContain('31');
    expect(pipe.transform('2026-07-31')).toContain('jul');

    // El 1 de enero es el caso donde equivocarse cambia también mes y año.
    expect(pipe.transform('2026-01-01')).toContain('01');
    expect(pipe.transform('2026-01-01')).toContain('ene');
    expect(pipe.transform('2026-01-01')).toContain('2026');
  });

  it('a una fecha sin hora no le inventa una hora', () => {
    // Pedirle 'datetime' a un valor que no la trae mostraría 00:00, que es
    // una hora que nadie escribió.
    expect(pipe.transform('2026-07-31', 'datetime')).not.toMatch(/\d{2}:\d{2}/);
  });

  it('usa un guion largo para lo que no tiene fecha', () => {
    expect(pipe.transform(null)).toBe('—');
    expect(pipe.transform(undefined)).toBe('—');
    expect(pipe.transform('')).toBe('—');
  });

  it('no revienta con una fecha inválida', () => {
    expect(pipe.transform('no-es-una-fecha')).toBe('—');
  });
});
