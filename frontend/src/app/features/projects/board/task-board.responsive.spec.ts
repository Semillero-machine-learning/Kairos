/**
 * HU-14 — Usar la plataforma desde el teléfono (RNF-01).
 *
 * Los nombres de los escenarios son los de `docs/user-stories.md`.
 *
 * Lo que decide si hay arrastrar y soltar es una media query, y eso sí se
 * prueba de verdad con un `matchMedia` fingido: jsdom no calcula CSS, así que
 * «veo cinco columnas» o «veo una lista» no se puede afirmar desde aquí — eso
 * se comprobó en el navegador durante la auditoría, con capturas a 360 y a
 * 1440. Lo que se fija aquí es la regla de negocio de la interfaz: por debajo
 * de 768 px no se arrastra, aunque haya ratón.
 */
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TASK_STATUS_ORDER, Task } from '../../../core/api/models';
import { mediaQuery } from '../../../shared/media-query';
import { DRAG_QUERY } from './task-board.page';
import { TaskCardComponent } from './task-card.component';

const original = window.matchMedia;

/** Un `matchMedia` que responde según el ancho y el puntero del caso. */
function fakeMatchMedia(width: number, pointer: 'fine' | 'coarse') {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  window.matchMedia = ((query: string) => {
    const minWidth = /min-width:\s*(\d+)px/.exec(query);
    const widthOk = minWidth ? width >= Number(minWidth[1]) : true;
    const pointerOk = query.includes('pointer: fine') ? pointer === 'fine' : true;
    return {
      matches: widthOk && pointerOk,
      media: query,
      addEventListener: (_: string, cb: (event: MediaQueryListEvent) => void) =>
        listeners.add(cb),
      removeEventListener: (_: string, cb: (event: MediaQueryListEvent) => void) =>
        listeners.delete(cb),
    } as unknown as MediaQueryList;
  }) as typeof window.matchMedia;
}

const TAREA: Task = {
  id: 't-1',
  project_id: 'p-1',
  title: 'Entrenar el modelo base',
  description: null,
  status: 'TODO',
  periodicity: 'ONE_TIME',
  due_date: '2026-09-18',
  is_overdue: false,
  assignees: [],
  created_by: { id: 'u-1', full_name: 'Ana Moreno' },
  created_at: '2026-09-09T14:00:00Z',
  updated_at: '2026-09-09T14:00:00Z',
  completed_at: null,
} as unknown as Task;

/** Anfitrión mínimo: la tarjeta con el valor que le pasaría el tablero. */
@Component({
  imports: [TaskCardComponent],
  template: `<app-task-card [task]="task" [canMove]="true" [canDrag]="canDrag()" />`,
})
class Host {
  readonly task = TAREA;
  readonly canDrag = mediaQuery(DRAG_QUERY);
}

function renderCard() {
  const fixture = TestBed.createComponent(Host);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('HU-14 — Usar la plataforma desde el teléfono', () => {
  beforeEach(() => {
    TestBed.resetTestingModule();
  });

  afterEach(() => {
    window.matchMedia = original;
    vi.restoreAllMocks();
  });

  it('Tablero en móvil', () => {
    // Dado que abro un proyecto en una pantalla de 360 px de ancho
    fakeMatchMedia(360, 'coarse');
    const host = renderCard();

    // Y cada tarea tiene un selector para cambiar de estado
    const selector = host.querySelector('select');
    expect(selector).not.toBeNull();
    expect(selector?.getAttribute('aria-label')).toContain('Entrenar el modelo base');

    // Y no hay arrastrar y soltar
    expect(host.querySelector('article')?.getAttribute('draggable')).toBe('false');
  });

  it('Tablero en móvil, incluso con ratón conectado', () => {
    // El ancho manda: una ventana estrecha en el escritorio apila las columnas
    // igual que un teléfono, y sin columnas no hay a dónde arrastrar.
    fakeMatchMedia(360, 'fine');

    expect(renderCard().querySelector('article')?.getAttribute('draggable')).toBe('false');
  });

  it('Tablero en escritorio', () => {
    // Dado que abro un proyecto en una pantalla de 1440 px
    fakeMatchMedia(1440, 'fine');
    const host = renderCard();

    // Entonces veo las cinco columnas del Kanban
    expect(TASK_STATUS_ORDER).toHaveLength(5);

    // Y puedo arrastrar tareas entre columnas
    expect(host.querySelector('article')?.getAttribute('draggable')).toBe('true');
  });

  it('Tablero en tableta táctil: ancho de sobra, pero se apunta con el dedo', () => {
    fakeMatchMedia(1024, 'coarse');

    expect(renderCard().querySelector('article')?.getAttribute('draggable')).toBe('false');
  });
});

describe('mediaQuery', () => {
  afterEach(() => {
    window.matchMedia = original;
  });

  it('se entera cuando la ventana cambia de tamaño', () => {
    const listeners: ((event: MediaQueryListEvent) => void)[] = [];
    window.matchMedia = ((query: string) =>
      ({
        matches: false,
        media: query,
        addEventListener: (_: string, cb: (event: MediaQueryListEvent) => void) =>
          listeners.push(cb),
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList) as typeof window.matchMedia;

    TestBed.resetTestingModule();
    const fixture = TestBed.createComponent(Host);
    fixture.detectChanges();
    expect(fixture.componentInstance.canDrag()).toBe(false);

    // El navegador avisa de que ahora sí se cumple: la señal tiene que seguirlo.
    listeners.forEach((cb) => cb({ matches: true } as MediaQueryListEvent));
    expect(fixture.componentInstance.canDrag()).toBe(true);
  });

  it('sin matchMedia no rompe y se queda en la variante sin lujos', () => {
    (window as unknown as { matchMedia?: unknown }).matchMedia = undefined;

    TestBed.resetTestingModule();
    const fixture = TestBed.createComponent(Host);
    fixture.detectChanges();

    expect(fixture.componentInstance.canDrag()).toBe(false);
  });
});
