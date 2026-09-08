import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import { NotificationSettings } from '../../core/api/models';
import { NotificationsApi } from '../../core/api/notifications.api';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

/** Los que ofrece la interfaz. El backend admite cualquiera entre 0 y 30, pero
 * una casilla por día sería una pared de casillas: estos cubren los ritmos que
 * un semillero usa de verdad. */
const OFFERED_DAYS = [7, 5, 3, 2, 1, 0] as const;

const DAY_LABEL: Record<number, string> = {
  7: 'Una semana antes',
  5: '5 días antes',
  3: '3 días antes',
  2: '2 días antes',
  1: 'El día anterior',
  0: 'El mismo día',
};

const MAX_DAYS = 5;

/**
 * Configuración global de recordatorios (RF-43, RN-26, HU-11).
 *
 * Es una sola fila para toda la plataforma: no hay versión por proyecto y no
 * debería haberla. La zona horaria no es editable —RN-26 la fija en
 * `America/Bogota`— y se muestra como dato, no como campo: un desplegable
 * apagado invita a preguntar por qué está apagado.
 */
@Component({
  selector: 'app-notification-settings-page',
  imports: [
    FormsModule,
    PageHeaderComponent,
    AlertComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-2xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header
        title="Notificaciones"
        description="Cuándo se avisa de una fecha límite. Aplica a todos los proyectos por igual."
      />

      @if (loading()) {
        <div class="flex items-center gap-2 py-12 text-sm text-ink-muted">
          <ui-spinner />
          Cargando la configuración…
        </div>
      } @else if (loadError()) {
        <div class="py-8">
          <ui-alert tone="error">{{ loadError() }}</ui-alert>
        </div>
      } @else {
        <form class="grid gap-7 py-8" (ngSubmit)="save()">
          @if (error()) {
            <ui-alert tone="error">{{ error() }}</ui-alert>
          }
          @if (saved()) {
            <ui-alert tone="success">La configuración quedó guardada.</ui-alert>
          }

          <fieldset class="grid gap-3">
            <legend class="text-sm font-medium text-ink">Aviso previo</legend>
            <p class="max-w-prose text-sm text-ink-muted">
              Cada responsable recibe un aviso los días marcados. Máximo {{ maxDays }}.
            </p>
            <div class="grid gap-1 sm:grid-cols-2">
              @for (day of offeredDays; track day) {
                <label
                  class="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-[var(--radius-control)] px-3 text-sm text-ink transition-colors hover:bg-sunken"
                >
                  <input
                    type="checkbox"
                    class="size-4 shrink-0 accent-accent"
                    [checked]="days().includes(day)"
                    [disabled]="saving() || (atLimit() && !days().includes(day))"
                    (change)="toggleDay(day)"
                  />
                  {{ label(day) }}
                </label>
              }
            </div>
            @if (days().length === 0) {
              <p class="text-sm text-notice">
                Sin ningún día marcado no se envían avisos previos. Los de tareas vencidas siguen su
                propio interruptor.
              </p>
            }
          </fieldset>

          <ui-field
            label="Hora de envío"
            for="hora-envio"
            hint="Hora de Colombia. El proceso se dispara una vez al día."
          >
            <select uiInput id="hora-envio" name="hora" [(ngModel)]="sendHour" class="sm:max-w-48">
              @for (hour of hours; track hour) {
                <option [value]="hour">{{ hourLabel(hour) }}</option>
              }
            </select>
          </ui-field>

          <label
            class="flex min-h-11 cursor-pointer items-start gap-2.5 text-sm text-ink sm:items-center"
          >
            <input
              type="checkbox"
              class="mt-0.5 size-4 shrink-0 accent-accent sm:mt-0"
              name="vencidas"
              [(ngModel)]="overdueEnabled"
            />
            <span>
              Avisar también de las tareas vencidas
              <span class="block text-ink-muted">
                Se notifica a los responsables y a quien pueda revisar la tarea.
              </span>
            </span>
          </label>

          <p class="text-sm text-ink-muted">
            Zona horaria: <strong class="font-medium text-ink">{{ timezone() }}</strong
            >. Es fija para toda la plataforma.
          </p>

          <div class="flex">
            <ui-button type="submit" [loading]="saving()">Guardar</ui-button>
          </div>
        </form>
      }
    </div>
  `,
})
export class NotificationSettingsPage {
  private readonly api = inject(NotificationsApi);

  protected readonly offeredDays = OFFERED_DAYS;
  protected readonly maxDays = MAX_DAYS;
  protected readonly hours = Array.from({ length: 24 }, (_, hour) => hour);

  protected readonly loading = signal(true);
  protected readonly loadError = signal('');
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly saved = signal(false);

  private readonly daysSignal = signal<number[]>([]);
  protected readonly days = this.daysSignal.asReadonly();
  protected readonly timezone = signal('America/Bogota');

  protected sendHour = 7;
  protected overdueEnabled = true;

  protected readonly atLimit = computed(() => this.daysSignal().length >= MAX_DAYS);

  constructor() {
    this.api.settings().subscribe({
      next: (settings) => {
        this.apply(settings);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.loadError.set(err.message);
        this.loading.set(false);
      },
    });
  }

  protected label(day: number): string {
    return DAY_LABEL[day] ?? `${day} días antes`;
  }

  protected hourLabel(hour: number): string {
    return `${String(hour).padStart(2, '0')}:00`;
  }

  protected toggleDay(day: number): void {
    this.saved.set(false);
    this.daysSignal.update((current) =>
      current.includes(day)
        ? current.filter((value) => value !== day)
        : // De mayor a menor: el orden en que se dispararán.
          [...current, day].sort((a, b) => b - a),
    );
  }

  protected save(): void {
    this.saving.set(true);
    this.error.set('');
    this.saved.set(false);
    this.api
      .saveSettings({
        reminder_days_before: this.daysSignal(),
        // El desplegable devuelve texto aunque las opciones sean números.
        send_hour: Number(this.sendHour),
        overdue_enabled: this.overdueEnabled,
      })
      .subscribe({
        next: (settings) => {
          this.apply(settings);
          this.saved.set(true);
          this.saving.set(false);
        },
        error: (err: ApiError) => {
          this.error.set(err.message);
          this.saving.set(false);
        },
      });
  }

  /** La respuesta manda: si el backend normalizó algo, se pinta lo que quedó
   * guardado y no lo que se envió. */
  private apply(settings: NotificationSettings): void {
    this.daysSignal.set([...settings.reminder_days_before].sort((a, b) => b - a));
    this.sendHour = settings.send_hour;
    this.overdueEnabled = settings.overdue_enabled;
    this.timezone.set(settings.timezone);
  }
}
