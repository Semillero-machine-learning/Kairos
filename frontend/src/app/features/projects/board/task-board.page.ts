import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';

import { ApiError, fieldMessage } from '../../../core/api/api-error';
import {
  TASK_PERIODICITY_LABEL,
  TASK_STATUS_LABEL,
  TASK_STATUS_ORDER,
  ProjectMember,
  Submission,
  Task,
  TaskPeriodicity,
  TaskStatus,
} from '../../../core/api/models';
import { ProjectsApi } from '../../../core/api/projects.api';
import { SubmissionBody, TasksApi } from '../../../core/api/tasks.api';
import { SessionService } from '../../../core/auth/session.service';
import { AlertComponent } from '../../../shared/ui/alert.component';
import { ButtonComponent } from '../../../shared/ui/button.component';
import { DialogComponent } from '../../../shared/ui/dialog.component';
import { EmptyStateComponent } from '../../../shared/ui/empty-state.component';
import { InputDirective } from '../../../shared/ui/input.directive';
import { SpinnerComponent } from '../../../shared/ui/spinner.component';
import { ProjectStore } from '../project.store';
import { BoardStore } from './board.store';
import { TaskCardComponent } from './task-card.component';
import { TaskDetailComponent } from './task-detail.component';
import { TaskEditorComponent, TaskFormValue } from './task-editor.component';
import { canMoveTo } from './transitions';

type DialogMode = 'closed' | 'create' | 'edit' | 'detail';

const PERIODICITIES: TaskPeriodicity[] = ['ONE_TIME', 'WEEKLY', 'MONTHLY', 'SEMESTER'];

/**
 * El tablero Kanban del proyecto (RF-29).
 *
 * Por debajo de 768 px las cinco columnas se apilan como listas por estado y no
 * hay arrastrar y soltar: en un teléfono es incómodo y propenso a errores, y el
 * selector de cada tarjeta es más rápido y más accesible (RNF-01, HU-14). Ese
 * mismo selector es el camino por teclado en escritorio, donde arrastrar no
 * tiene equivalente (RNF-09).
 */
@Component({
  selector: 'app-task-board-page',
  imports: [
    FormsModule,
    AlertComponent,
    ButtonComponent,
    DialogComponent,
    EmptyStateComponent,
    InputDirective,
    SpinnerComponent,
    TaskCardComponent,
    TaskDetailComponent,
    TaskEditorComponent,
  ],
  providers: [BoardStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="py-6">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 class="text-sm font-medium text-ink">
          {{ board.tasks().length }}
          {{ board.tasks().length === 1 ? 'tarea' : 'tareas' }}
          @if (board.hasFilters()) {
            <span class="font-normal text-ink-muted">con los filtros puestos</span>
          }
        </h2>

        @if (projectStore.can('task.create')) {
          <ui-button size="sm" (pressed)="openCreate()">Nueva tarea</ui-button>
        }
      </div>

      <!-- Filtros (RF-36) -->
      <div class="mt-4 flex flex-wrap items-center gap-2">
        <label class="sr-only" for="filtro-responsable">Filtrar por responsable</label>
        <select
          uiInput
          [compact]="true"
          id="filtro-responsable"
          class="w-full sm:w-52"
          [ngModel]="board.filters().assigneeId"
          (ngModelChange)="board.setFilters({ assigneeId: $event })"
        >
          <option value="">Todos los responsables</option>
          @for (member of members(); track member.user.id) {
            <option [value]="member.user.id">{{ member.user.full_name }}</option>
          }
        </select>

        <label class="sr-only" for="filtro-periodicidad">Filtrar por periodicidad</label>
        <select
          uiInput
          [compact]="true"
          id="filtro-periodicidad"
          class="w-full sm:w-44"
          [ngModel]="board.filters().periodicity"
          (ngModelChange)="board.setFilters({ periodicity: $event })"
        >
          <option value="">Toda periodicidad</option>
          @for (option of periodicities; track option) {
            <option [value]="option">{{ periodicityLabel(option) }}</option>
          }
        </select>

        <label
          class="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-[var(--radius-control)] px-2 text-sm text-ink"
        >
          <input
            type="checkbox"
            class="size-4 accent-[var(--color-accent)]"
            [ngModel]="board.filters().overdue"
            (ngModelChange)="board.setFilters({ overdue: $event })"
          />
          Solo vencidas
        </label>

        @if (board.hasFilters()) {
          <ui-button variant="ghost" size="sm" (pressed)="board.clearFilters()">
            Quitar filtros
          </ui-button>
        }
      </div>

      @if (board.actionError()) {
        <div class="mt-4">
          <ui-alert tone="error">{{ board.actionError() }}</ui-alert>
        </div>
      }

      @if (board.loading()) {
        <div class="flex items-center gap-2.5 py-12 text-sm text-ink-muted">
          <ui-spinner [size]="18" />
          <span>Cargando el tablero…</span>
        </div>
      } @else if (board.error()) {
        <div class="mt-5">
          <ui-alert tone="error">{{ board.error() }}</ui-alert>
        </div>
      } @else if (!board.tasks().length) {
        <ui-empty-state
          [title]="board.hasFilters() ? 'Ninguna tarea coincide' : 'El tablero está vacío'"
          [description]="
            board.hasFilters()
              ? 'Prueba a quitar algún filtro para ver el resto del tablero.'
              : 'Las tareas del proyecto aparecen aquí, repartidas en cinco columnas según cómo van.'
          "
        >
          @if (board.hasFilters()) {
            <ui-button variant="secondary" (pressed)="board.clearFilters()">
              Quitar filtros
            </ui-button>
          } @else if (projectStore.can('task.create')) {
            <ui-button (pressed)="openCreate()">Crear la primera tarea</ui-button>
          }
        </ui-empty-state>
      } @else {
        <!--
          Una columna por estado. En móvil el grid es de una sola columna, así
          que las cinco quedan apiladas como listas; desde 768 px fluyen en fila
          con desplazamiento horizontal, y desde 1024 se reparten el ancho.
        -->
        <div
          class="mt-5 grid gap-4 md:auto-cols-[minmax(14rem,1fr)] md:grid-flow-col md:overflow-x-auto md:pb-2 lg:auto-cols-fr lg:gap-3"
        >
          @for (status of statuses; track status) {
            <section
              class="min-w-0 rounded-[var(--radius-panel)] border bg-sunken p-2.5 transition-colors"
              [class.border-line]="dropTarget() !== status"
              [class.border-accent]="dropTarget() === status"
              [attr.aria-label]="columnLabel(status)"
              (dragover)="onDragOver($event, status)"
              (dragleave)="onDragLeave(status)"
              (drop)="onDrop(status)"
            >
              <h3
                class="flex items-baseline justify-between px-1 pb-2 text-sm font-medium text-ink"
              >
                {{ label(status) }}
                <span class="text-xs font-normal text-ink-muted">
                  {{ board.byStatus()[status].length }}
                </span>
              </h3>

              <ul class="grid gap-2">
                @for (task of board.byStatus()[status]; track task.id) {
                  <li>
                    <app-task-card
                      [task]="task"
                      [canMove]="canMove(task)"
                      [canDrag]="pointerIsFine() && canMove(task)"
                      (opened)="openDetail(task)"
                      (statusPicked)="board.move(task, $event)"
                      (dragStarted)="dragged.set(task)"
                      (dragEnded)="endDrag()"
                    />
                  </li>
                } @empty {
                  <li class="px-1 py-3 text-xs text-ink-faint">Nada por aquí.</li>
                }
              </ul>
            </section>
          }
        </div>
      }
    </div>

    <ui-dialog
      [open]="mode() !== 'closed'"
      [label]="mode() === 'detail' ? 'Detalle de la tarea' : 'Formulario de tarea'"
      (closed)="closeDialog()"
    >
      @if (mode() === 'detail') {
        <app-task-detail
          [task]="selected()"
          [members]="members()"
          [submissions]="submissions()"
          [canEdit]="projectStore.can('task.edit_any')"
          [canDelete]="projectStore.can('task.delete')"
          [canAssign]="projectStore.can('task.assign')"
          [isAssignee]="isAssignee()"
          [busy]="busy()"
          [error]="dialogError()"
          (editRequested)="mode.set('edit')"
          (deleteRequested)="deleteTask()"
          (assigneeAdded)="addAssignee($event)"
          (assigneeRemoved)="removeAssignee($event)"
          (submitted)="submitWork($event)"
        />
      } @else if (mode() !== 'closed') {
        <app-task-editor
          [task]="mode() === 'edit' ? selected() : null"
          [members]="members()"
          [saving]="busy()"
          [error]="dialogError()"
          [today]="today"
          (submitted)="save($event)"
          (cancelled)="closeDialog()"
        />
      }
    </ui-dialog>
  `,
})
export class TaskBoardPage {
  protected readonly projectStore = inject(ProjectStore);
  protected readonly board = inject(BoardStore);
  private readonly tasksApi = inject(TasksApi);
  private readonly projectsApi = inject(ProjectsApi);
  private readonly session = inject(SessionService);

  protected readonly statuses = TASK_STATUS_ORDER;
  protected readonly periodicities = PERIODICITIES;
  /** Hoy en Colombia, para avisar de una fecha límite ya pasada. */
  protected readonly today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
  }).format(new Date());

  protected readonly members = signal<ProjectMember[]>([]);
  protected readonly submissions = signal<Submission[]>([]);
  protected readonly mode = signal<DialogMode>('closed');
  protected readonly selected = signal<Task | null>(null);
  protected readonly busy = signal(false);
  protected readonly dialogError = signal('');

  protected readonly dragged = signal<Task | null>(null);
  protected readonly dropTarget = signal<TaskStatus | null>(null);

  /**
   * Si el dispositivo apunta con precisión. Arrastrar y soltar se ofrece solo
   * ahí: se consulta el puntero y no el ancho, porque una tableta de 1024 px
   * con dedo tiene el mismo problema que un teléfono.
   */
  protected readonly pointerIsFine = signal(
    typeof window !== 'undefined' && window.matchMedia('(pointer: fine)').matches,
  );

  protected readonly isAssignee = computed(() => {
    const userId = this.session.user()?.id;
    return !!userId && !!this.selected()?.assignees.some((person) => person.id === userId);
  });

  constructor() {
    const projectId = this.projectStore.project()?.id;
    if (projectId) {
      this.board.load(projectId);
      this.projectsApi.members(projectId).subscribe({
        next: (members) => this.members.set(members),
        error: () => this.members.set([]),
      });
    }
  }

  protected label(status: TaskStatus): string {
    return TASK_STATUS_LABEL[status];
  }

  protected columnLabel(status: TaskStatus): string {
    return `${TASK_STATUS_LABEL[status]}: ${this.board.byStatus()[status].length} tareas`;
  }

  protected periodicityLabel(periodicity: TaskPeriodicity): string {
    return TASK_PERIODICITY_LABEL[periodicity];
  }

  /** Quien tiene `task.change_status_any`, o el responsable de esa tarea (RN-10). */
  protected canMove(task: Task): boolean {
    if (this.projectStore.can('task.change_status_any')) return true;
    const userId = this.session.user()?.id;
    return !!userId && task.assignees.some((person) => person.id === userId);
  }

  // --- Arrastrar y soltar ---

  protected onDragOver(event: DragEvent, status: TaskStatus): void {
    const task = this.dragged();
    if (!task || !this.canMove(task) || !canMoveTo(task.status, status)) return;
    // Sin `preventDefault` el navegador no admite el soltar: es la forma de
    // decir que esta columna sí acepta esta tarjeta.
    event.preventDefault();
    this.dropTarget.set(status);
  }

  protected onDragLeave(status: TaskStatus): void {
    if (this.dropTarget() === status) this.dropTarget.set(null);
  }

  protected onDrop(status: TaskStatus): void {
    const task = this.dragged();
    this.endDrag();
    if (task && task.status !== status) this.board.move(task, status);
  }

  protected endDrag(): void {
    this.dragged.set(null);
    this.dropTarget.set(null);
  }

  // --- Diálogo ---

  protected openCreate(): void {
    this.selected.set(null);
    this.dialogError.set('');
    this.mode.set('create');
  }

  protected openDetail(task: Task): void {
    this.selected.set(task);
    this.submissions.set([]);
    this.dialogError.set('');
    this.mode.set('detail');
    this.tasksApi.submissions(task.id).subscribe({
      next: (submissions) => this.submissions.set(submissions),
      error: () => this.submissions.set([]),
    });
  }

  protected closeDialog(): void {
    this.mode.set('closed');
    this.selected.set(null);
    this.dialogError.set('');
  }

  // --- Acciones ---

  protected save(value: TaskFormValue): void {
    const task = this.mode() === 'edit' ? this.selected() : null;
    this.busy.set(true);
    this.dialogError.set('');

    const request = task
      ? this.tasksApi.update(task.id, {
          title: value.title,
          description: value.description,
          periodicity: value.periodicity,
          due_date: value.due_date,
        })
      : this.tasksApi.create(this.projectStore.project()!.id, value);

    request.subscribe({
      next: (saved) => {
        this.board.replace(saved);
        this.projectStore.refresh();
        this.busy.set(false);
        this.closeDialog();
      },
      error: (err: ApiError) => {
        this.dialogError.set(fieldMessage(err));
        this.busy.set(false);
      },
    });
  }

  protected deleteTask(): void {
    const task = this.selected();
    if (!task) return;
    this.busy.set(true);
    this.tasksApi.remove(task.id).subscribe({
      next: () => {
        this.board.remove(task.id);
        this.projectStore.refresh();
        this.busy.set(false);
        this.closeDialog();
      },
      error: (err: ApiError) => {
        this.dialogError.set(fieldMessage(err));
        this.busy.set(false);
      },
    });
  }

  protected addAssignee(userId: string): void {
    const task = this.selected();
    if (!task) return;
    this.mutate(this.tasksApi.addAssignee(task.id, userId));
  }

  protected removeAssignee(userId: string): void {
    const task = this.selected();
    if (!task) return;
    this.mutate(this.tasksApi.removeAssignee(task.id, userId));
  }

  protected submitWork(body: SubmissionBody): void {
    const task = this.selected();
    if (!task) return;
    this.busy.set(true);
    this.dialogError.set('');
    this.tasksApi.submit(task.id, body).subscribe({
      next: (submission) => {
        this.submissions.update((current) => [submission, ...current]);
        // La entrega mueve la tarea a revisión en la misma transacción (RF-31),
        // así que hay que releerla para que el tablero no muestre el estado
        // anterior.
        this.tasksApi.get(task.id).subscribe({
          next: (updated) => {
            this.board.replace(updated);
            this.selected.set(updated);
            this.projectStore.refresh();
          },
        });
        this.busy.set(false);
      },
      error: (err: ApiError) => {
        this.dialogError.set(fieldMessage(err));
        this.busy.set(false);
      },
    });
  }

  private mutate(request: Observable<Task>): void {
    this.busy.set(true);
    this.dialogError.set('');
    request.subscribe({
      next: (updated) => {
        this.board.replace(updated);
        this.selected.set(updated);
        this.busy.set(false);
      },
      error: (err: ApiError) => {
        this.dialogError.set(fieldMessage(err));
        this.busy.set(false);
      },
    });
  }
}
