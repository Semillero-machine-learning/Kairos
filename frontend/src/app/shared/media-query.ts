import { DestroyRef, Signal, inject, signal } from '@angular/core';

/**
 * Señal que sigue una media query del navegador.
 *
 * Se lee al crearla y se vuelve a leer cuando el navegador avisa del cambio.
 * Consultar `matchMedia` una sola vez, al construir el componente, deja el
 * valor congelado: una ventana que se estrecha, una tableta que rota o un
 * teclado que se conecta cambian la respuesta y la interfaz no se entera.
 *
 * Hay que llamarla dentro de un contexto de inyección (el inicializador de un
 * campo de componente, por ejemplo): se apunta al `DestroyRef` para soltar el
 * oyente cuando el componente se va.
 */
export function mediaQuery(query: string): Signal<boolean> {
  // En una prueba sin DOM, o al renderizar en servidor, no hay `matchMedia`.
  // Devolver `false` es lo prudente: en la duda, la variante sin lujos.
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return signal(false).asReadonly();
  }

  const list = window.matchMedia(query);
  const matches = signal(list.matches);
  const onChange = (event: MediaQueryListEvent) => matches.set(event.matches);

  list.addEventListener('change', onChange);
  inject(DestroyRef).onDestroy(() => list.removeEventListener('change', onChange));

  return matches.asReadonly();
}
