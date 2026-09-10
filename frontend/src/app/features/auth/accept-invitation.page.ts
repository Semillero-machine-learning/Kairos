import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import { AuthApi } from '../../core/api/auth.api';
import { PASSWORD_HINT, PASSWORD_MIN_LENGTH, PASSWORD_TOO_SHORT } from '../../core/auth/password';
import { SessionService } from '../../core/auth/session.service';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PasswordInputComponent } from '../../shared/ui/password-input.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { AuthLayoutComponent } from './auth-layout.component';

/**
 * Aceptación de invitación (RF-03, HU-02).
 *
 * El correo llega del backend al validar el token y se muestra precargado y no
 * editable. Si el token venció o ya se usó, se dice eso y nada más: nunca se
 * revela si el correo ya tiene cuenta.
 */
@Component({
  selector: 'app-accept-invitation-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    AuthLayoutComponent,
    AlertComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
    PasswordInputComponent,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-auth-layout
      [title]="email() ? 'Crea tu cuenta' : 'Invitación'"
      [subtitle]="email() ? 'Te invitaron al semillero. Define tu nombre y tu contraseña.' : ''"
    >
      @if (checking()) {
        <div class="flex items-center gap-2.5 text-sm text-ink-muted">
          <ui-spinner [size]="18" />
          <span>Comprobando la invitación…</span>
        </div>
      } @else if (invalidReason()) {
        <ui-alert tone="error">{{ invalidReason() }}</ui-alert>
        <p class="mt-5 text-sm leading-relaxed text-ink-muted">
          Pídele al administrador del semillero que te envíe una invitación nueva.
        </p>
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

          <ui-field label="Correo" for="email" hint="Es el correo al que llegó la invitación.">
            <input uiInput id="email" type="email" [value]="email()" disabled />
          </ui-field>

          <ui-field label="Nombre completo" for="fullName" [error]="nameError()">
            <input
              uiInput
              id="fullName"
              type="text"
              formControlName="fullName"
              autocomplete="name"
              [invalid]="!!nameError()"
              [attr.aria-describedby]="nameError() ? 'fullName-msg' : null"
            />
          </ui-field>

          <ui-field
            label="Contraseña"
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

          <ui-button type="submit" [full]="true" [loading]="submitting()">
            Crear mi cuenta
          </ui-button>
        </form>
      }
    </app-auth-layout>
  `,
})
export class AcceptInvitationPage {
  /** Llega de la ruta `/invitacion/:token` por `withComponentInputBinding`. */
  readonly token = input.required<string>();

  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApi);
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);

  protected readonly passwordHint = PASSWORD_HINT;

  protected readonly checking = signal(true);
  protected readonly submitting = signal(false);
  protected readonly submitted = signal(false);
  protected readonly email = signal('');
  protected readonly invalidReason = signal('');
  protected readonly error = signal('');

  protected readonly form = this.fb.nonNullable.group({
    fullName: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]],
  });

  constructor() {
    // El token se valida al abrir el enlace, antes de mostrar el formulario:
    // así el escenario "token vencido" de HU-02 no obliga a llenar nada.
    queueMicrotask(() => this.check());
  }

  private check(): void {
    this.authApi.invitationInfo(this.token()).subscribe({
      next: ({ email }) => {
        this.email.set(email);
        this.checking.set(false);
      },
      error: (err: ApiError) => {
        this.checking.set(false);
        this.invalidReason.set(
          err.is('NOT_FOUND')
            ? 'Este enlace de invitación no existe o ya fue utilizado.'
            : err.message,
        );
      },
    });
  }

  protected nameError(): string {
    const control = this.form.controls.fullName;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Escribe tu nombre completo.';
    if (control.hasError('minlength')) return 'El nombre debe tener al menos 2 caracteres.';
    if (control.hasError('maxlength')) return 'El nombre no puede pasar de 120 caracteres.';
    return '';
  }

  protected passwordError(): string {
    const control = this.form.controls.password;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Define una contraseña.';
    if (control.hasError('minlength')) return PASSWORD_TOO_SHORT;
    return '';
  }

  protected submit(): void {
    this.submitted.set(true);
    this.error.set('');
    if (this.form.invalid || this.submitting()) return;

    const { fullName, password } = this.form.getRawValue();
    this.submitting.set(true);

    this.authApi.acceptInvitation(this.token(), fullName, password).subscribe({
      next: (tokens) => {
        // La respuesta ya trae la sesión: se entra sin pasar por el ingreso.
        this.session.adopt(tokens);
        void this.router.navigate(['/inicio']);
      },
      error: (err: ApiError) => {
        this.submitting.set(false);
        if (err.is('INVITATION_EXPIRED', 'INVITATION_ALREADY_USED', 'NOT_FOUND')) {
          this.invalidReason.set(err.message);
          return;
        }
        this.error.set(err.message);
      },
    });
  }
}
