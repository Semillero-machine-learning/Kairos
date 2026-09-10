import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import { AuthApi } from '../../core/api/auth.api';
import { PASSWORD_HINT, PASSWORD_MIN_LENGTH, PASSWORD_TOO_SHORT } from '../../core/auth/password';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PasswordInputComponent } from '../../shared/ui/password-input.component';
import { AuthLayoutComponent } from './auth-layout.component';

/** Las dos contraseñas deben coincidir. Se valida en el grupo, no en el campo,
 * porque depende de los dos a la vez. */
function passwordsMatch(group: AbstractControl): { mismatch: true } | null {
  const password = group.get('password')?.value;
  const confirmation = group.get('confirmation')?.value;
  return password && confirmation && password !== confirmation ? { mismatch: true } : null;
}

/**
 * Definición de la contraseña nueva desde el enlace del correo
 * (RF-07, RN-42, HU-03).
 *
 * Al confirmar, el backend revoca todas las sesiones anteriores, así que aquí
 * no se adopta ninguna sesión: se manda a ingresar con la contraseña nueva.
 */
@Component({
  selector: 'app-reset-password-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    AuthLayoutComponent,
    AlertComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
    PasswordInputComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-auth-layout
      title="Define tu contraseña nueva"
      [subtitle]="done() ? '' : 'Al guardarla se cerrarán todas tus sesiones abiertas.'"
    >
      @if (done()) {
        <ui-alert tone="success">
          Listo. Tu contraseña quedó cambiada y las sesiones anteriores se cerraron.
        </ui-alert>
        <div class="mt-6">
          <a
            routerLink="/ingresar"
            class="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            Ingresar
          </a>
        </div>
      } @else {
        <form class="flex flex-col gap-5" [formGroup]="form" (ngSubmit)="submit()">
          @if (error()) {
            <ui-alert tone="error">{{ error() }}</ui-alert>
          }

          <ui-field
            label="Contraseña nueva"
            for="password"
            [hint]="passwordHint"
            [error]="passwordError()"
          >
            <ui-password-input>
              <input
                uiInput
                [trailingSlot]="true"
                id="password"
                type="password"
                formControlName="password"
                autocomplete="new-password"
                [invalid]="!!passwordError()"
                aria-describedby="password-msg"
              />
            </ui-password-input>
          </ui-field>

          <ui-field label="Repite la contraseña" for="confirmation" [error]="confirmationError()">
            <ui-password-input>
              <input
                uiInput
                [trailingSlot]="true"
                id="confirmation"
                type="password"
                formControlName="confirmation"
                autocomplete="new-password"
                [invalid]="!!confirmationError()"
                [attr.aria-describedby]="confirmationError() ? 'confirmation-msg' : null"
              />
            </ui-password-input>
          </ui-field>

          <ui-button type="submit" [full]="true" [loading]="submitting()">
            Guardar la contraseña
          </ui-button>
        </form>

        <p class="mt-6 text-center text-sm">
          <a routerLink="/recuperar" class="text-ink-muted underline hover:text-ink">
            Pedir un enlace nuevo
          </a>
        </p>
      }
    </app-auth-layout>
  `,
})
export class ResetPasswordPage {
  /** Llega de la ruta `/restablecer/:token`. */
  readonly token = input.required<string>();

  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApi);

  protected readonly passwordHint = PASSWORD_HINT;

  protected readonly submitting = signal(false);
  protected readonly submitted = signal(false);
  protected readonly done = signal(false);
  protected readonly error = signal('');

  protected readonly form = this.fb.nonNullable.group(
    {
      password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]],
      confirmation: ['', [Validators.required]],
    },
    { validators: passwordsMatch },
  );

  protected passwordError(): string {
    const control = this.form.controls.password;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Define una contraseña.';
    if (control.hasError('minlength')) return PASSWORD_TOO_SHORT;
    return '';
  }

  protected confirmationError(): string {
    const control = this.form.controls.confirmation;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Repite la contraseña.';
    return this.form.hasError('mismatch') ? 'Las dos contraseñas no coinciden.' : '';
  }

  protected submit(): void {
    this.submitted.set(true);
    this.error.set('');
    if (this.form.invalid || this.submitting()) return;

    this.submitting.set(true);
    this.authApi.confirmPasswordReset(this.token(), this.form.getRawValue().password).subscribe({
      next: () => {
        this.submitting.set(false);
        this.done.set(true);
      },
      error: (err: ApiError) => {
        this.submitting.set(false);
        this.error.set(
          err.is('NOT_FOUND')
            ? 'Este enlace ya no sirve: venció o ya se usó. Pide uno nuevo.'
            : err.message,
        );
      },
    });
  }
}
