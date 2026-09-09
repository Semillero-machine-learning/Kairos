import { describe, expect, it } from 'vitest';

import { canMove, moveBy } from './ordering';

describe('ordering', () => {
  it('sube un elemento intercambiándolo con el anterior', () => {
    expect(moveBy(['a', 'b', 'c'], 1, -1)).toEqual(['b', 'a', 'c']);
  });

  it('baja un elemento intercambiándolo con el siguiente', () => {
    expect(moveBy(['a', 'b', 'c'], 1, 1)).toEqual(['a', 'c', 'b']);
  });

  it('no deja salirse por los extremos', () => {
    expect(moveBy(['a', 'b'], 0, -1)).toEqual(['a', 'b']);
    expect(moveBy(['a', 'b'], 1, 1)).toEqual(['a', 'b']);
  });

  it('no muta el arreglo original', () => {
    const original = ['a', 'b'];

    moveBy(original, 0, 1);

    expect(original).toEqual(['a', 'b']);
  });

  it('canMove dice cuándo el botón va apagado', () => {
    expect(canMove(3, 0, -1)).toBe(false);
    expect(canMove(3, 0, 1)).toBe(true);
    expect(canMove(3, 2, 1)).toBe(false);
    expect(canMove(1, 0, 1)).toBe(false);
  });
});
