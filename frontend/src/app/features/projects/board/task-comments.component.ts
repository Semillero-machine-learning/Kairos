import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { TaskComment } from '../../../core/api/models';
import { BogotaDatePipe } from '../../../shared/pipes/bogota-date.pipe';
import { ButtonComponent } from '../../../shared/ui/button.component';
import { InputDirective } from '../../../shared/ui/input.directive';

/** Lo que sale del formulario de edición: qué comentario y con qué texto. */
export interface CommentEdit {
  id: string;
  body: string;
}

/**
 * El hilo de comentarios de una tarea (RF-35).
 *
 * Vive aparte del detalle porque es la única parte de esa pantalla con estado
 * propio —qué comentario se está editando— y meterlo dentro haría que abrir una
 * entrega y editar un comentario compartieran variables sin ninguna razón.
 *
 * Los botones aparecen según RN-11: el autor edita y borra lo suyo, y quien
 * tiene `task.delete` puede retirar un comentario ajeno para moderar, pero
 * nadie reescribe palabras de otro. Ocultarlos es comodidad; el backend vuelve
 * a decidirlo en cada petición.
 */
@Component({
  selector: 'app-task-comments',
  imports: [FormsModule, BogotaDatePipe, ButtonComponent, InputDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="mt-6 border-t border-line pt-5" aria-labelledby="detalle-comentarios">
      <h3 id="detalle-comentarios" class="text-sm font-medium text-ink">
        Comentarios
        @if (comments().length) {
          <span class="ml-1 font-normal text-ink-muted">({{ comments().length }})</span>
        }
      </h3>

      @if (comments().length) {
        <ul class="mt-3 grid gap-3">
          @for (comment of comments(); track comment.id) {
            <li class="rounded-[var(--radius-control)] border border-line bg-sunken p-3">
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs text-ink-muted">
                <span class="font-medium text-ink">{{ comment.author.full_name }}</span>
                <span>{{ comment.created_at | bogotaDate: 'datetime' }}</span>
                @if (comment.updated_at !== comment.created_at) {
                  <span>· editado</span>
                }
              </div>

              @if (editingId() === comment.id) {
                <div class="mt-2 grid gap-2">
                  <textarea
                    uiInput
                    rows="3"
                    class="min-h-20 py-2.5"
                    maxlength="4000"
                    [attr.aria-label]="'Editar el comentario de ' + comment.author.full_name"
                    [(ngModel)]="draft"
                  ></textarea>
                  <div class="flex flex-wrap gap-2">
                    <ui-button
                      size="sm"
                      [disabled]="!draft.trim() || busy()"
                      (pressed)="confirmEdit(comment)"
                    >
                      Guardar
                    </ui-button>
                    <ui-button size="sm" variant="ghost" (pressed)="cancelEdit()">
                      Cancelar
                    </ui-button>
                  </div>
                </div>
              } @else {
                <p class="mt-1.5 text-sm leading-relaxed whitespace-pre-line text-ink">
                  {{ comment.body }}
                </p>

                @if (canEdit(comment) || canRemove(comment)) {
                  <div class="mt-2 flex flex-wrap gap-2">
                    @if (canEdit(comment)) {
                      <ui-button size="sm" variant="ghost" (pressed)="startEdit(comment)">
                        Editar
                      </ui-button>
                    }
                    @if (canRemove(comment)) {
                      @if (confirmingId() === comment.id) {
                        <ui-button
                          size="sm"
                          variant="danger"
                          [loading]="busy()"
                          (pressed)="removed.emit(comment.id)"
                        >
                          Confirmar que se borra
                        </ui-button>
                        <ui-button size="sm" variant="ghost" (pressed)="confirmingId.set(null)">
                          Mejor no
                        </ui-button>
                      } @else {
                        <ui-button
                          size="sm"
                          variant="ghost"
                          (pressed)="confirmingId.set(comment.id)"
                        >
                          Borrar
                        </ui-button>
                      }
                    }
                  </div>
                }
              }
            </li>
          }
        </ul>
      } @else {
        <p class="mt-2 text-sm text-ink-muted">
          Todavía no hay comentarios. Aquí se acuerdan las cosas que no caben en la descripción.
        </p>
      }

      @if (canComment()) {
        <form class="mt-4 grid gap-2" (ngSubmit)="add()">
          <textarea
            uiInput
            id="comentario-nuevo"
            name="comentario"
            rows="2"
            class="min-h-20 py-2.5"
            maxlength="4000"
            placeholder="Escribe un comentario…"
            aria-label="Escribir un comentario"
            [(ngModel)]="newComment"
          ></textarea>
          <div class="flex">
            <ui-button type="submit" size="sm" [disabled]="!newComment.trim()" [loading]="busy()">
              Comentar
            </ui-button>
          </div>
        </form>
      }
    </section>
  `,
})
export class TaskCommentsComponent {
  readonly comments = input<TaskComment[]>([]);
  readonly currentUserId = input<string | null>(null);
  /** `task.comment` en el proyecto. */
  readonly canComment = input(false);
  /** `task.delete`: permite retirar un comentario ajeno (RN-11). */
  readonly canModerate = input(false);
  readonly busy = input(false);

  readonly added = output<string>();
  readonly edited = output<CommentEdit>();
  readonly removed = output<string>();

  protected readonly editingId = signal<string | null>(null);
  protected readonly confirmingId = signal<string | null>(null);

  protected newComment = '';
  protected draft = '';

  private readonly userId = computed(() => this.currentUserId());

  protected canEdit(comment: TaskComment): boolean {
    return this.userId() === comment.author.id;
  }

  protected canRemove(comment: TaskComment): boolean {
    return this.canEdit(comment) || this.canModerate();
  }

  protected startEdit(comment: TaskComment): void {
    this.confirmingId.set(null);
    this.editingId.set(comment.id);
    this.draft = comment.body;
  }

  protected cancelEdit(): void {
    this.editingId.set(null);
    this.draft = '';
  }

  protected confirmEdit(comment: TaskComment): void {
    const body = this.draft.trim();
    if (!body) return;
    this.edited.emit({ id: comment.id, body });
    this.cancelEdit();
  }

  /**
   * Vacía la caja al enviar, al revés que el formulario de entrega.
   *
   * Un comentario de dos líneas se vuelve a escribir sin drama si algo falla, y
   * dejarlo puesto haría que el siguiente empezara con el texto del anterior.
   */
  protected add(): void {
    const body = this.newComment.trim();
    if (!body) return;
    this.newComment = '';
    this.added.emit(body);
  }
}
