import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  SUBMISSION_STATUS_LABEL,
  TASK_PERIODICITY_LABEL,
  TASK_STATUS_LABEL,
  ProjectMember,
  Submission,
  Task,
} from '../../../core/api/models';
import { SubmissionBody } from '../../../core/api/tasks.api';
import { BogotaDatePipe } from '../../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../../shared/ui/alert.component';
import { BadgeComponent } from '../../../shared/ui/badge.component';
import { ButtonComponent } from '../../../shared/ui/button.component';
import { FieldComponent } from '../../../shared/ui/field.component';
import { InputDirective } from '../../../shared/ui/input.directive';

/**
 * El detalle de una tarea: lo que la tarjeta no cabe.
 *
 * Cada acción aparece según los permisos del proyecto, que es comodidad, no
 * seguridad: quien llame al endpoint sin ellos recibe 403 igual (RNF-05).
 * Registrar la entrega no depende de un permiso sino de ser responsable, que es
 * una regla de propiedad (RN-10).
 */
@Component({
  selector: 'app-task-detail',
  imports: [
    FormsModule,
    BogotaDatePipe,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (task(); as task) {
      <div class="flex items-start justify-between gap-4">
        <h2 class="text-base font-semibold text-balance text-ink">{{ task.title }}</h2>
        <ui-badge [tone]="task.is_overdue ? 'danger' : 'neutral'">
          {{ statusLabel(task) }}
        </ui-badge>
      </div>

      <dl class="mt-4 grid gap-x-5 gap-y-3 text-sm sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">Fecha límite</dt>
          <dd class="mt-0.5 text-ink">
            {{ task.due_date ? (task.due_date | bogotaDate) : 'Sin fecha' }}
            @if (task.is_overdue) {
              <span class="text-danger">· vencida</span>
            }
          </dd>
        </div>
        <div>
          <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">Periodicidad</dt>
          <dd class="mt-0.5 text-ink">{{ periodicity(task) }}</dd>
        </div>
        <div class="sm:col-span-2">
          <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">Creada por</dt>
          <dd class="mt-0.5 text-ink">
            {{ task.created_by.full_name }} · {{ task.created_at | bogotaDate }}
          </dd>
        </div>
      </dl>

      @if (task.description) {
        <p class="mt-4 max-w-prose text-sm leading-relaxed whitespace-pre-line text-ink">
          {{ task.description }}
        </p>
      }

      @if (error()) {
        <div class="mt-4">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      <!-- Responsables -->
      <section class="mt-6 border-t border-line pt-5" aria-labelledby="detalle-responsables">
        <h3 id="detalle-responsables" class="text-sm font-medium text-ink">Responsables</h3>

        @if (task.assignees.length) {
          <ul class="mt-2 flex flex-wrap gap-1.5">
            @for (person of task.assignees; track person.id) {
              <li
                class="inline-flex items-center gap-1 rounded-full border border-line bg-surface py-0.5 pr-1 pl-2.5 text-xs text-ink"
              >
                {{ person.full_name }}
                @if (canAssign()) {
                  <button
                    type="button"
                    class="grid size-7 any-pointer-coarse:size-11 place-items-center rounded-full text-ink-muted transition-colors hover:bg-sunken hover:text-danger"
                    [attr.aria-label]="'Quitar a ' + person.full_name + ' de la tarea'"
                    [disabled]="busy()"
                    (click)="assigneeRemoved.emit(person.id)"
                  >
                    ×
                  </button>
                }
              </li>
            }
          </ul>
        } @else {
          <p class="mt-2 text-sm text-ink-muted">
            Sin responsable. Nadie recibirá recordatorios de esta tarea.
          </p>
        }

        @if (canAssign() && assignable().length) {
          <label class="mt-3 flex flex-col gap-1.5 sm:max-w-xs">
            <span class="text-sm text-ink-muted">Agregar responsable</span>
            <select
              uiInput
              [compact]="true"
              class="w-full"
              [disabled]="busy()"
              [value]="''"
              (change)="onAssign($event)"
            >
              <option value="">Elige a alguien del proyecto…</option>
              @for (member of assignable(); track member.user.id) {
                <option [value]="member.user.id">{{ member.user.full_name }}</option>
              }
            </select>
          </label>
        }
      </section>

      <!-- Entrega -->
      <section class="mt-6 border-t border-line pt-5" aria-labelledby="detalle-entrega">
        <h3 id="detalle-entrega" class="text-sm font-medium text-ink">Entrega</h3>

        @if (canSubmit()) {
          <form class="mt-3 grid gap-3" (ngSubmit)="submit()">
            <ui-field
              label="Qué hiciste"
              for="entrega-descripcion"
              hint="Queda como constancia del trabajo. Mínimo 10 caracteres."
            >
              <textarea
                uiInput
                id="entrega-descripcion"
                name="entrega"
                rows="3"
                class="min-h-24 py-2.5"
                required
                minlength="10"
                maxlength="4000"
                [(ngModel)]="description"
              ></textarea>
            </ui-field>

            <ui-field
              label="Enlace en GitHub"
              for="entrega-url"
              [optional]="true"
              hint="El commit, el pull request o el árbol del repositorio."
            >
              <input
                uiInput
                id="entrega-url"
                name="url"
                type="url"
                inputmode="url"
                placeholder="https://github.com/semillero-ml/anomalias/commit/a1b2c3d"
                [(ngModel)]="commitUrl"
              />
            </ui-field>

            <div class="flex">
              <ui-button type="submit" [loading]="busy()">Entregar y pasar a revisión</ui-button>
            </div>
          </form>
        } @else if (task.status === 'IN_REVIEW') {
          <p class="mt-2 text-sm text-ink-muted">Entregada y esperando revisión.</p>
        } @else if (isAssignee()) {
          <p class="mt-2 text-sm text-ink-muted">
            La entrega se registra con la tarea en «{{ inProgressLabel }}».
          </p>
        } @else {
          <p class="mt-2 text-sm text-ink-muted">
            Solo quien es responsable de la tarea puede entregar.
          </p>
        }

        @if (submissions().length) {
          <ul class="mt-4 grid gap-3">
            @for (submission of submissions(); track submission.id) {
              <li class="rounded-[var(--radius-control)] border border-line bg-sunken p-3">
                <div class="flex flex-wrap items-center gap-2 text-xs text-ink-muted">
                  <ui-badge [tone]="tone(submission)">{{ reviewLabel(submission) }}</ui-badge>
                  <span>{{ submission.submitted_by.full_name }}</span>
                  <span>· {{ submission.created_at | bogotaDate: 'datetime' }}</span>
                </div>
                <p class="mt-2 text-sm leading-relaxed whitespace-pre-line text-ink">
                  {{ submission.description }}
                </p>
                @if (submission.commit_url; as url) {
                  <a
                    [href]="url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="mt-1.5 inline-block text-sm break-all text-accent underline"
                  >
                    {{ url }}
                  </a>
                }
                @if (submission.review_comment; as comment) {
                  <p class="mt-2 text-sm text-ink-muted">Revisión: {{ comment }}</p>
                }
              </li>
            }
          </ul>
        }
      </section>

      <!-- Acciones -->
      @if (canEdit() || canDelete()) {
        <div class="mt-6 flex flex-col gap-2 border-t border-line pt-5 sm:flex-row-reverse">
          @if (canEdit()) {
            <ui-button variant="secondary" (pressed)="editRequested.emit()">Editar</ui-button>
          }
          @if (canDelete()) {
            @if (confirming()) {
              <ui-button variant="danger" [loading]="busy()" (pressed)="deleteRequested.emit()">
                Confirmar que se elimina
              </ui-button>
              <ui-button variant="ghost" (pressed)="confirming.set(false)"> Mejor no </ui-button>
            } @else {
              <ui-button variant="ghost" (pressed)="confirming.set(true)">Eliminar</ui-button>
            }
          }
        </div>
      }
    }
  `,
})
export class TaskDetailComponent {
  readonly task = input.required<Task | null>();
  readonly members = input<ProjectMember[]>([]);
  readonly submissions = input<Submission[]>([]);
  readonly canEdit = input(false);
  readonly canDelete = input(false);
  readonly canAssign = input(false);
  readonly isAssignee = input(false);
  readonly busy = input(false);
  readonly error = input('');

  readonly editRequested = output<void>();
  readonly deleteRequested = output<void>();
  readonly assigneeAdded = output<string>();
  readonly assigneeRemoved = output<string>();
  readonly submitted = output<SubmissionBody>();

  protected readonly inProgressLabel = TASK_STATUS_LABEL.IN_PROGRESS;
  protected readonly confirming = signal(false);

  protected description = '';
  protected commitUrl = '';

  /** Un `computed` sobre el identificador y no la tarea entera: así el efecto de
   * abajo corre al cambiar de tarea, y no cada vez que la misma tarea vuelve del
   * backend como un objeto nuevo. */
  private readonly taskId = computed(() => this.task()?.id);

  constructor() {
    // Abrir otra tarea empieza de cero: ni el borrador de la entrega anterior ni
    // una confirmación de borrado a medio armar deben viajar de una a otra.
    effect(() => {
      this.taskId();
      this.description = '';
      this.commitUrl = '';
      this.confirming.set(false);
    });
  }

  /** RF-31: la entrega es lo que lleva la tarea de «En progreso» a revisión. */
  protected readonly canSubmit = computed(
    () => this.isAssignee() && this.task()?.status === 'IN_PROGRESS',
  );

  protected readonly assignable = computed(() => {
    const already = new Set(this.task()?.assignees.map((person) => person.id) ?? []);
    return this.members().filter((member) => !already.has(member.user.id));
  });

  protected statusLabel(task: Task): string {
    return TASK_STATUS_LABEL[task.status];
  }

  protected periodicity(task: Task): string {
    return TASK_PERIODICITY_LABEL[task.periodicity];
  }

  protected reviewLabel(submission: Submission): string {
    return SUBMISSION_STATUS_LABEL[submission.review_status];
  }

  protected tone(submission: Submission): 'neutral' | 'success' | 'danger' {
    if (submission.review_status === 'APPROVED') return 'success';
    if (submission.review_status === 'REJECTED') return 'danger';
    return 'neutral';
  }

  protected onAssign(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const userId = select.value;
    select.value = '';
    if (userId) this.assigneeAdded.emit(userId);
  }

  /**
   * Entrega lo escrito, **sin** vaciar el formulario.
   *
   * Si el backend la acepta, la tarea pasa a revisión y el formulario
   * desaparece solo, porque `canSubmit` deja de ser cierto. Si la rechaza —una
   * URL que no es de GitHub, por ejemplo—, lo escrito sigue ahí para corregirlo:
   * limpiarlo antes de saber el resultado le borra el trabajo a quien acaba de
   * redactarlo.
   */
  protected submit(): void {
    this.submitted.emit({
      description: this.description.trim(),
      commit_url: this.commitUrl.trim() || null,
    });
  }
}
