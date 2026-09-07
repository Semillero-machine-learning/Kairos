import { TaskStatus } from '../../../core/api/models';

/**
 * A qué estados ofrece pasar la interfaz desde cada estado.
 *
 * Es una transcripción de la tabla de `business-rules.md` §4, y una comodidad:
 * quien llame al endpoint con una transición que no existe recibe un 409 igual.
 * Sirve para no ofrecer un destino que se sabe imposible, no para autorizar
 * nada (RNF-05).
 *
 * Dos filas se apartan de la tabla a propósito:
 *
 * - `IN_PROGRESS → IN_REVIEW` existe, pero exige registrar una entrega (RF-31),
 *   así que la interfaz lo ofrece como la acción «Entregar» y no como un cambio
 *   de estado suelto, que siempre respondería `SUBMISSION_REQUIRED`.
 * - Las dos que salen de `IN_REVIEW` son la revisión de la entrega (RN-07,
 *   RN-09), y llegan con la Fase 4. Hasta entonces, una tarea en revisión no se
 *   mueve desde aquí.
 */
export const STATUS_TARGETS: Record<TaskStatus, readonly TaskStatus[]> = {
  BACKLOG: ['TODO'],
  TODO: ['IN_PROGRESS', 'BACKLOG'],
  IN_PROGRESS: ['TODO'],
  IN_REVIEW: [],
  DONE: ['IN_PROGRESS'],
};

/** Si la interfaz debe permitir soltar una tarjeta sobre esa columna. */
export function canMoveTo(from: TaskStatus, to: TaskStatus): boolean {
  return STATUS_TARGETS[from].includes(to);
}
