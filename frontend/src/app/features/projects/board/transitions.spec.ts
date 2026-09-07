import { describe, expect, it } from 'vitest';

import { TASK_STATUS_ORDER, TaskStatus } from '../../../core/api/models';
import { STATUS_TARGETS, canMoveTo } from './transitions';

/**
 * La tabla de `business-rules.md` §4, transcrita a mano desde el documento y no
 * desde el código. Dos copias independientes que tienen que coincidir es justo
 * lo que hace útil esta prueba, igual que en `test_task_transitions.py`.
 */
const TABLA: [TaskStatus, TaskStatus][] = [
  ['BACKLOG', 'TODO'],
  ['TODO', 'IN_PROGRESS'],
  ['TODO', 'BACKLOG'],
  ['IN_PROGRESS', 'TODO'],
  ['IN_PROGRESS', 'IN_REVIEW'],
  ['IN_REVIEW', 'DONE'],
  ['IN_REVIEW', 'IN_PROGRESS'],
  ['DONE', 'IN_PROGRESS'],
];

/**
 * Las tres que la interfaz no ofrece como cambio de estado suelto, con el
 * motivo por el que no lo hace.
 */
const NO_OFRECIDAS: [TaskStatus, TaskStatus][] = [
  // Exige registrar una entrega: es la acción «Entregar» (RF-31).
  ['IN_PROGRESS', 'IN_REVIEW'],
  // Aprobar marca la entrega; devolver exige comentario (RN-07, RN-09).
  ['IN_REVIEW', 'DONE'],
  ['IN_REVIEW', 'IN_PROGRESS'],
];

describe('STATUS_TARGETS', () => {
  it('no ofrece ninguna transición que la tabla no tenga', () => {
    for (const from of TASK_STATUS_ORDER) {
      for (const to of STATUS_TARGETS[from]) {
        expect(
          TABLA.some(([source, target]) => source === from && target === to),
          `${from} → ${to} no está en business-rules.md §4`,
        ).toBe(true);
      }
    }
  });

  it('ofrece todas las de la tabla salvo las que van por otra acción', () => {
    for (const [from, to] of TABLA) {
      const esperada = !NO_OFRECIDAS.some(([s, t]) => s === from && t === to);
      expect(canMoveTo(from, to), `${from} → ${to}`).toBe(esperada);
    }
  });

  it('una tarea en revisión no se mueve desde el tablero', () => {
    expect(STATUS_TARGETS.IN_REVIEW).toEqual([]);
  });

  it('rechaza los saltos que la tabla no contempla', () => {
    expect(canMoveTo('TODO', 'DONE')).toBe(false);
    expect(canMoveTo('BACKLOG', 'IN_PROGRESS')).toBe(false);
    expect(canMoveTo('IN_REVIEW', 'TODO')).toBe(false);
  });
});
