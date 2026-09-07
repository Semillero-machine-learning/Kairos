import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import { InvitationsApi } from '../../core/api/invitations.api';
import {
  GLOBAL_ROLE_LABEL,
  GlobalRole,
  INVITATION_STATUS_LABEL,
  Invitation,
  InvitationCreated,
  InvitationStatus,
} from '../../core/api/models';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent, BadgeTone } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

const STATUS_TONES: Record<InvitationStatus, BadgeTone> = {
  PENDING: 'notice',
  ACCEPTED: 'success',
  REVOKED: 'neutral',
  EXPIRED: 'neutral',
};

/**
 * Invitaciones a la plataforma (RF-01, RF-02, RF-04, HU-01).
 *
 * `invite_url` solo viaja una vez, al crear o reenviar: después el backend
 * únicamente guarda el hash del token. Por eso el enlace se muestra en un
 * aviso persistente que hay que cerrar a mano, y no en un mensaje que se
 * desvanece solo.
 */
@Component({
  selector: 'app-invitations-page',
  imports: [
    FormsModule,
    ReactiveFormsModule,
    BogotaDatePipe,
    PageHeaderComponent,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    FieldComponent,
    InputDirective,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header
        title="Invitaciones"
        description="El registro es cerrado: nadie crea una cuenta por su cuenta. Una invitación vence a los 7 días."
      />

      <!-- Crear -->
      <section class="mt-8" aria-labelledby="nueva">
        <h2 id="nueva" class="text-sm font-medium text-ink">Invitar a alguien</h2>

        <form
          class="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start"
          [formGroup]="form"
          (ngSubmit)="create()"
        >
          <div class="flex-1">
            <ui-field label="Correo" for="invite-email" [error]="emailError()">
              <input
                uiInput
                id="invite-email"
                type="email"
                formControlName="email"
                inputmode="email"
                placeholder="persona@ejemplo.com"
                [invalid]="!!emailError()"
                [attr.aria-describedby]="emailError() ? 'invite-email-msg' : null"
              />
            </ui-field>
          </div>
          <div class="sm:w-52">
            <ui-field label="Rol global" for="invite-role">
              <select uiInput id="invite-role" formControlName="globalRole">
                <option value="MEMBER">Miembro</option>
                <option value="LESSON_EDITOR">Editor de lecciones</option>
                <option value="ADMIN">Administrador</option>
              </select>
            </ui-field>
          </div>
          <div class="sm:pt-7">
            <ui-button type="submit" [loading]="creating()">Enviar invitación</ui-button>
          </div>
        </form>

        @if (createError()) {
          <div class="mt-4">
            <ui-alert tone="error">{{ createError() }}</ui-alert>
          </div>
        }

        @if (lastCreated(); as created) {
          <div class="mt-4">
            <ui-alert tone="success">
              <p class="font-medium">
                Invitación enviada a {{ created.email }}.
              </p>
              <p class="mt-1.5">
                Este enlace se muestra una sola vez. Cópialo si quieres enviarlo también por otro
                canal.
              </p>
              <div class="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
                <code
                  class="min-w-0 flex-1 truncate rounded-[var(--radius-control)] border border-success-line bg-surface px-2.5 py-2 font-mono text-xs text-ink"
                >
                  {{ created.invite_url }}
                </code>
                <div class="flex shrink-0 gap-2">
                  <ui-button variant="secondary" size="sm" (pressed)="copy(created.invite_url)">
                    {{ copied() ? 'Copiado' : 'Copiar' }}
                  </ui-button>
                  <ui-button variant="ghost" size="sm" (pressed)="lastCreated.set(null)">
                    Cerrar
                  </ui-button>
                </div>
              </div>
            </ui-alert>
          </div>
        }
      </section>

      <!-- Lista -->
      <section class="mt-10 border-t border-line pt-8" aria-labelledby="listado">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="listado" class="text-sm font-medium text-ink">Invitaciones enviadas</h2>
          <div class="flex items-center gap-2.5">
            <label for="filtro-estado" class="shrink-0 text-sm text-ink-muted">Estado</label>
            <select
              uiInput
              id="filtro-estado"
              class="!w-44"
              [ngModel]="statusFilter()"
              (ngModelChange)="onStatusChange($event)"
            >
              <option value="">Todas</option>
              <option value="PENDING">Pendientes</option>
              <option value="ACCEPTED">Aceptadas</option>
              <option value="REVOKED">Revocadas</option>
              <option value="EXPIRED">Vencidas</option>
            </select>
          </div>
        </div>

        @if (listError()) {
          <div class="mt-4">
            <ui-alert tone="error">{{ listError() }}</ui-alert>
          </div>
        }

        <div class="mt-5 border-t border-line">
          @if (loading()) {
            <div class="flex items-center gap-2.5 px-1 py-10 text-sm text-ink-muted">
              <ui-spinner [size]="18" />
              <span>Cargando invitaciones…</span>
            </div>
          } @else if (invitations().length === 0) {
            <ui-empty-state
              title="Ninguna invitación"
              [description]="
                statusFilter()
                  ? 'No hay invitaciones en ese estado.'
                  : 'Cuando invites a alguien, la invitación aparece aquí con su estado y su fecha de vencimiento.'
              "
            />
          } @else {
            <ul>
              @for (invitation of invitations(); track invitation.id) {
                <li
                  class="grid grid-cols-1 gap-3 border-b border-line py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium text-ink">{{ invitation.email }}</p>
                    <p class="text-sm text-ink-muted">{{ roleLabel(invitation.global_role) }}</p>
                    <p class="mt-1 text-xs text-ink-muted">
                      @if (invitation.status === 'ACCEPTED') {
                        Aceptada el {{ invitation.accepted_at | bogotaDate }}
                      } @else {
                        Vence el {{ invitation.expires_at | bogotaDate: 'datetime' }}
                      }
                    </p>
                  </div>

                  <div class="flex flex-wrap items-center gap-2 sm:justify-end">
                    <ui-badge [tone]="statusTone(invitation.status)">
                      {{ statusLabel(invitation.status) }}
                    </ui-badge>

                    @if (invitation.status === 'PENDING') {
                      <ui-button
                        variant="secondary"
                        size="sm"
                        [loading]="busyId() === invitation.id"
                        (pressed)="resend(invitation)"
                      >
                        Reenviar
                      </ui-button>
                      <ui-button
                        variant="ghost"
                        size="sm"
                        [disabled]="busyId() === invitation.id"
                        (pressed)="revoke(invitation)"
                      >
                        Revocar
                      </ui-button>
                    }
                  </div>
                </li>
              }
            </ul>
          }
        </div>
      </section>
    </div>
  `,
})
export class InvitationsPage {
  private readonly invitationsApi = inject(InvitationsApi);
  private readonly fb = inject(FormBuilder);

  protected readonly invitations = signal<Invitation[]>([]);
  protected readonly loading = signal(true);
  protected readonly listError = signal('');
  protected readonly createError = signal('');
  protected readonly creating = signal(false);
  protected readonly submitted = signal(false);
  protected readonly busyId = signal<string | null>(null);
  protected readonly copied = signal(false);
  protected readonly statusFilter = signal<InvitationStatus | ''>('');

  /** El enlace recién generado. Se conserva hasta que el administrador lo
   * cierra: no se puede volver a consultar. */
  protected readonly lastCreated = signal<InvitationCreated | null>(null);

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    globalRole: ['MEMBER' as GlobalRole, [Validators.required]],
  });

  constructor() {
    this.load();
  }

  protected statusLabel(status: InvitationStatus): string {
    return INVITATION_STATUS_LABEL[status];
  }

  protected statusTone(status: InvitationStatus): BadgeTone {
    return STATUS_TONES[status];
  }

  protected roleLabel(role: GlobalRole): string {
    return GLOBAL_ROLE_LABEL[role];
  }

  protected emailError(): string {
    const control = this.form.controls.email;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Escribe el correo de la persona.';
    if (control.hasError('email')) return 'Ese correo no tiene un formato válido.';
    return '';
  }

  protected onStatusChange(value: InvitationStatus | ''): void {
    this.statusFilter.set(value);
    this.load();
  }

  protected create(): void {
    this.submitted.set(true);
    this.createError.set('');
    if (this.form.invalid || this.creating()) return;

    const { email, globalRole } = this.form.getRawValue();
    this.creating.set(true);

    this.invitationsApi.create(email, globalRole).subscribe({
      next: (created) => {
        this.creating.set(false);
        this.submitted.set(false);
        this.copied.set(false);
        this.lastCreated.set(created);
        this.form.reset({ email: '', globalRole: 'MEMBER' });
        this.load();
      },
      error: (err: ApiError) => {
        this.creating.set(false);
        this.createError.set(err.message);
      },
    });
  }

  protected resend(invitation: Invitation): void {
    this.listError.set('');
    this.busyId.set(invitation.id);

    this.invitationsApi.resend(invitation.id).subscribe({
      next: (created) => {
        this.busyId.set(null);
        this.copied.set(false);
        // Reenviar invalida el token anterior y devuelve uno nuevo (RF-04).
        this.lastCreated.set(created);
        this.load();
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.listError.set(err.message);
      },
    });
  }

  protected revoke(invitation: Invitation): void {
    this.listError.set('');
    this.busyId.set(invitation.id);

    this.invitationsApi.revoke(invitation.id).subscribe({
      next: () => {
        this.busyId.set(null);
        this.load();
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.listError.set(err.message);
      },
    });
  }

  protected copy(url: string): void {
    navigator.clipboard.writeText(url).then(
      () => this.copied.set(true),
      () => this.copied.set(false),
    );
  }

  private load(): void {
    this.loading.set(true);
    this.listError.set('');

    this.invitationsApi.list(this.statusFilter() || undefined).subscribe({
      next: (items) => {
        this.invitations.set(items);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.loading.set(false);
        this.listError.set(err.message);
      },
    });
  }
}
