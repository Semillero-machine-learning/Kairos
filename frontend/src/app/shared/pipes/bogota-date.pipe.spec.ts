import { describe, expect, it } from 'vitest';

import { BogotaDatePipe } from './bogota-date.pipe';

describe('BogotaDatePipe', () => {
  const pipe = new BogotaDatePipe();

  it('presenta en America/Bogota lo que el backend guarda en UTC (RNF-06)', () => {
    // 02:30 UTC del día 7 son las 21:30 del día 6 en Colombia: la fecha cambia.
    expect(pipe.transform('2026-09-07T02:30:00Z')).toContain('06');
    expect(pipe.transform('2026-09-07T02:30:00Z', 'datetime')).toContain('09:30');
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
