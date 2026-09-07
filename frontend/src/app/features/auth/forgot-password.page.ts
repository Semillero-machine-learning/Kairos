import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import { AuthApi } from '../../core/api/auth.api';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { AuthLayoutComponent } from './auth-layout.component';

/**
 * Solicitud de restablecimiento (RF-07, RN-41, HU-03).
 *
 * La respuesta es idéntica exista o no la cuenta, y la pantalla respeta eso:
 * el mensaje de confirmación está redactado para no afirmar que el correo
 * existe.
 */
@Component({
  selector: 'app-forgot-password-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    AuthLayoutComponent,
    AlertComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-auth-layout
      title="Recupera tu contraseña"
      [subtitle]="
        sent()
          ? ''
          : 'Escribe tu correo y te enviamos un enlace para definir una contraseña nueva.'
      "
    >
      @if (sent()) {
        <ui-alert tone="success">
          Si hay una cuenta con ese correo, en unos minutos llegará un enlace para restablecer la
          contraseña. El enlace vence en una hora.
        </ui-alert>
        <p class="mt-6 text-sm">
          <a routerLink="/ingresar" class="text-ink-muted underline hover:text-ink">
            Volver al ingreso
          </a>
        </p>
      } @else {
        <form class="flex flex-col gap-5" [formGroup]="form" (ngSubmit)="submit()">
          @if (error()) {
            <ui-alert tone="error">{{ error() }}</ui-alert>
          }

          <ui-field label="Correo" for="email" [error]="emailError()">
            <input
              uiInput
              id="email"
              type="email"
              formControlName="email"
              autocomplete="email"
              inputmode="email"
              placeholder="tucorreo@ejemplo.com"
              [invalid]="!!emailError()"
              [attr.aria-describedby]="emailError() ? 'email-msg' : null"
            />
          </ui-field>

          <ui-button type="submit" [full]="true" [loading]="submitting()">
            Enviar el enlace
          </ui-button>
        </form>

        <p class="mt-6 text-center text-sm">
          <a routerLink="/ingresar" class="text-ink-muted underline hover:text-ink">
            Volver al ingreso
          </a>
        </p>
      }
    </app-auth-layout>
  `,
})
export class ForgotPasswordPage {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApi);

  protected readonly submitting = signal(false);
  protected readonly submitted = signal(false);
  protected readonly sent = signal(false);
  protected readonly error = signal('');

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  protected emailError(): string {
    const control = this.form.controls.email;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Escribe tu correo.';
    if (control.hasError('email')) return 'Ese correo no tiene un formato válido.';
    return '';
  }

  protected submit(): void {
    this.submitted.set(true);
    this.error.set('');
    if (this.form.invalid || this.submitting()) return;

    this.submitting.set(true);
    this.authApi.requestPasswordReset(this.form.getRawValue().email).subscribe({
      next: () => {
        this.submitting.set(false);
        this.sent.set(true);
      },
      error: (err: ApiError) => {
        this.submitting.set(false);
        this.error.set(err.message);
      },
    });
  }
}
