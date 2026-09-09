/**
 * Reordenar con botones, no arrastrando.
 *
 * El arrastrar y soltar está desactivado por debajo de 768 px en todo el
 * sistema (RNF-01) y reordenar el catálogo no merece dos implementaciones. Un
 * par de botones de 44 px funciona igual en los tres tamaños, se maneja con el
 * teclado sin nada extra y no depende de la precisión del puntero.
 */

/** Intercambia un elemento con su vecino. Fuera de rango devuelve una copia
 * intacta, para que quien llama no tenga que comprobar los bordes. */
export function moveBy<T>(items: readonly T[], index: number, delta: number): T[] {
  const next = [...items];
  const target = index + delta;
  if (index < 0 || index >= next.length || target < 0 || target >= next.length) return next;
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

export function canMove(length: number, index: number, delta: number): boolean {
  const target = index + delta;
  return index >= 0 && index < length && target >= 0 && target < length;
}
