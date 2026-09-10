import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import {
  TASK_PERIODICITY_LABEL,
  TASK_STATUS_LABEL,
  Task,
  TaskStatus,
} from '../../../core/api/models';
import { BogotaDatePipe } from '../../../shared/pipes/bogota-date.pipe';
import { InputDirective } from '../../../shared/ui/input.directive';
import { STATUS_TARGETS } from './transitions';

/**
 * Una tarea en el tablero.
 *
 * El título es un botón y no la tarjeta entera: dentro hay un selector de
 * estado, y una tarjeta clicable que contiene otro control deja al teclado sin
 * forma de llegar al segundo.
 *
 * El selector aparece en todos los anchos, no solo en móvil. Arrastrar y soltar
 * no tiene equivalente por teclado, así que este es el camino que hace el
 * tablero operable sin ratón (RNF-09); en móvil, además, es el único (RNF-01).
 */
@Component({
  selector: 'app-task-card',
  imports: [BogotaDatePipe, InputDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article
      [draggable]="canDrag()"
      [class]="classes()"
      (dragstart)="dragStarted.emit()"
      (dragend)="dragEnded.emit()"
    >
      <!--
        Con el dedo, el título crece a 44 px de alto por dentro y recupera el
        espacio con el margen negativo: el área de toque cumple RNF-01 sin que
        las tarjetas cambien de alto ni el tablero se estire en el teléfono.
      -->
      <button
        type="button"
        class="block w-full text-left text-sm font-medium text-balance text-ink hover:text-accent any-pointer-coarse:-my-3 any-pointer-coarse:py-3"
        (click)="opened.emit()"
      >
        {{ task().title }}
      </button>

      <div class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        @if (task().is_overdue) {
          <span
            class="inline-flex items-center rounded-full border border-danger-line bg-danger-soft px-2 py-0.5 font-medium text-danger"
          >
            Vencida
          </span>
        }
        @if (task().due_date; as due) {
          <span class="text-ink-muted">{{ due | bogotaDate }}</span>
        }
        @if (task().periodicity !== 'ONE_TIME') {
          <span class="text-ink-muted">· {{ periodicityLabel() }}</span>
        }
      </div>

      <div class="mt-3 flex items-center gap-1.5">
        @if (task().assignees.length) {
          <span class="flex -space-x-1.5" [attr.aria-label]="'Responsables: ' + names()">
            @for (person of task().assignees.slice(0, 3); track person.id) {
              <span
                class="grid size-7 place-items-center rounded-full border border-surface bg-accent-soft text-xs font-semibold text-accent"
                aria-hidden="true"
              >
                {{ initials(person.full_name) }}
              </span>
            }
          </span>
          @if (task().assignees.length > 3) {
            <span class="text-xs text-ink-muted">+{{ task().assignees.length - 3 }}</span>
          }
        } @else {
          <span class="text-xs text-ink-muted">Sin responsable</span>
        }
      </div>

      @if (canMove() && targets().length) {
        <!-- Sin etiqueta visible: la columna es estrecha, y el propio control ya
             muestra el estado actual. Quien no la ve la oye por aria-label. -->
        <select
          uiInput
          [compact]="true"
          class="mt-3 w-full"
          [attr.aria-label]="'Estado de «' + task().title + '»: mover a otro estado'"
          [value]="''"
          (change)="onSelect($event)"
        >
          <option value="">{{ statusLabel(task().status) }}</option>
          @for (target of targets(); track target) {
            <option [value]="target">Mover a {{ statusLabel(target) }}</option>
          }
        </select>
      }
    </article>
  `,
})
export class TaskCardComponent {
  readonly task = input.required<Task>();
  /** Si esta persona puede mover esta tarea: tiene `task.change_status_any` o es
   * responsable (RN-10). Es comodidad; el backend vuelve a decidirlo. */
  readonly canMove = input(false);
  /** Arrastrar solo desde 768 px: en móvil es incómodo y propenso a errores. */
  readonly canDrag = input(false);

  readonly opened = output<void>();
  readonly statusPicked = output<TaskStatus>();
  readonly dragStarted = output<void>();
  readonly dragEnded = output<void>();

  protected readonly targets = computed(() => STATUS_TARGETS[this.task().status]);

  protected readonly periodicityLabel = computed(
    () => TASK_PERIODICITY_LABEL[this.task().periodicity],
  );

  protected readonly names = computed(() =>
    this.task()
      .assignees.map((person) => person.full_name)
      .join(', '),
  );

  protected readonly classes = computed(() =>
    [
      'rounded-[var(--radius-control)] border border-line bg-surface p-3',
      'transition-colors hover:border-line-strong',
      this.canDrag() ? 'cursor-grab active:cursor-grabbing' : '',
    ].join(' '),
  );

  protected statusLabel(status: TaskStatus): string {
    return TASK_STATUS_LABEL[status];
  }

  protected initials(fullName: string): string {
    return fullName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('');
  }

  protected onSelect(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const value = select.value as TaskStatus | '';
    // Vuelve al marcador: el estado real lo dicta la tarea cuando el backend
    // responde, no lo que quedó elegido en el control.
    select.value = '';
    if (value) this.statusPicked.emit(value);
  }
}
