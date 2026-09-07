import { ChangeDetectionStrategy, Component, effect, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  TASK_PERIODICITY_LABEL,
  ProjectMember,
  Task,
  TaskPeriodicity,
} from '../../../core/api/models';
import { AlertComponent } from '../../../shared/ui/alert.component';
import { ButtonComponent } from '../../../shared/ui/button.component';
import { FieldComponent } from '../../../shared/ui/field.component';
import { InputDirective } from '../../../shared/ui/input.directive';

export interface TaskFormValue {
  title: string;
  description: string | null;
  periodicity: TaskPeriodicity;
  due_date: string | null;
  assignee_ids: string[];
}

const PERIODICITIES: TaskPeriodicity[] = ['ONE_TIME', 'WEEKLY', 'MONTHLY', 'SEMESTER'];

/**
 * Alta y edición de una tarea.
 *
 * Los responsables se eligen solo al crear. Después se agregan y se quitan uno
 * a uno desde el detalle, que es como los expone la API y lo que permite que
 * cada cambio quede con su fecha y su autor.
 */
@Component({
  selector: 'app-task-editor',
  imports: [FormsModule, AlertComponent, ButtonComponent, FieldComponent, InputDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form (ngSubmit)="save()">
      <h2 class="text-base font-semibold text-ink">
        {{ task() ? 'Editar la tarea' : 'Nueva tarea' }}
      </h2>

      @if (error()) {
        <div class="mt-4">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      <div class="mt-5 grid gap-4">
        <ui-field label="Título" for="tarea-titulo">
          <input
            uiInput
            id="tarea-titulo"
            name="titulo"
            required
            minlength="3"
            maxlength="200"
            autocomplete="off"
            placeholder="Entrenar el modelo base"
            [(ngModel)]="title"
          />
        </ui-field>

        <ui-field
          label="Descripción"
          for="tarea-descripcion"
          [optional]="true"
          hint="Qué hay que hacer y con qué se da por terminada."
        >
          <textarea
            uiInput
            id="tarea-descripcion"
            name="descripcion"
            rows="3"
            class="min-h-24 py-2.5"
            maxlength="4000"
            [(ngModel)]="description"
          ></textarea>
        </ui-field>

        <div class="grid gap-4 sm:grid-cols-2">
          <ui-field
            label="Periodicidad"
            for="tarea-periodicidad"
            hint="Es una etiqueta: no crea tareas nuevas."
          >
            <select uiInput id="tarea-periodicidad" name="periodicidad" [(ngModel)]="periodicity">
              @for (option of periodicities; track option) {
                <option [value]="option">{{ label(option) }}</option>
              }
            </select>
          </ui-field>

          <ui-field label="Fecha límite" for="tarea-fecha" [optional]="true" [hint]="dueHint()">
            <input uiInput id="tarea-fecha" name="fecha" type="date" [(ngModel)]="dueDate" />
          </ui-field>
        </div>

        @if (!task()) {
          <fieldset class="border-0 p-0">
            <legend class="text-sm font-medium text-ink">
              Responsables <span class="font-normal text-ink-muted">(opcional)</span>
            </legend>
            @if (members().length) {
              <ul class="mt-2 grid gap-1 sm:grid-cols-2">
                @for (member of members(); track member.user.id) {
                  <li>
                    <label
                      class="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-[var(--radius-control)] px-2 text-sm text-ink hover:bg-sunken"
                    >
                      <input
                        type="checkbox"
                        class="size-4 accent-[var(--color-accent)]"
                        [checked]="assignees().has(member.user.id)"
                        (change)="toggle(member.user.id)"
                      />
                      {{ member.user.full_name }}
                    </label>
                  </li>
                }
              </ul>
            } @else {
              <p class="mt-2 text-sm text-ink-muted">
                El proyecto todavía no tiene más integrantes a quienes asignarle la tarea.
              </p>
            }
          </fieldset>
        }
      </div>

      <div class="mt-6 flex flex-col gap-2 sm:flex-row-reverse">
        <ui-button type="submit" [loading]="saving()">
          {{ task() ? 'Guardar cambios' : 'Crear la tarea' }}
        </ui-button>
        <ui-button variant="ghost" (pressed)="cancelled.emit()">Cancelar</ui-button>
      </div>
    </form>
  `,
})
export class TaskEditorComponent {
  /** Nula al crear; la tarea que se edita en otro caso. */
  readonly task = input<Task | null>(null);
  readonly members = input<ProjectMember[]>([]);
  readonly saving = input(false);
  readonly error = input('');
  /** Hoy en Colombia, en formato ISO, para avisar de una fecha ya pasada. */
  readonly today = input('');

  readonly submitted = output<TaskFormValue>();
  readonly cancelled = output<void>();

  protected readonly periodicities = PERIODICITIES;

  protected title = '';
  protected description = '';
  protected periodicity: TaskPeriodicity = 'ONE_TIME';
  protected dueDate = '';
  protected readonly assignees = signal<Set<string>>(new Set());

  /**
   * EB-10: una fecha pasada se acepta, y se avisa antes de guardar en vez de
   * rechazarla. Puede ser una tarea que se registra tarde.
   *
   * Es un método y no un `computed` a propósito: `dueDate` lo escribe `ngModel`
   * sobre un campo normal, que ningún `computed` puede observar. La llamada se
   * reevalúa con la detección de cambios que dispara el propio `ngModel`.
   */
  protected dueHint(): string {
    return this.dueDate && this.today() && this.dueDate < this.today()
      ? 'Esa fecha ya pasó: la tarea se creará marcada como vencida.'
      : '';
  }

  constructor() {
    effect(() => {
      const task = this.task();
      this.title = task?.title ?? '';
      this.description = task?.description ?? '';
      this.periodicity = task?.periodicity ?? 'ONE_TIME';
      this.dueDate = task?.due_date ?? '';
      this.assignees.set(new Set());
    });
  }

  protected label(periodicity: TaskPeriodicity): string {
    return TASK_PERIODICITY_LABEL[periodicity];
  }

  protected toggle(userId: string): void {
    this.assignees.update((current) => {
      const next = new Set(current);
      if (!next.delete(userId)) next.add(userId);
      return next;
    });
  }

  protected save(): void {
    this.submitted.emit({
      title: this.title.trim(),
      description: this.description.trim() || null,
      periodicity: this.periodicity,
      due_date: this.dueDate || null,
      assignee_ids: [...this.assignees()],
    });
  }
}
