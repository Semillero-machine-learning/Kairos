import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthApi } from '../../core/api/auth.api';
import { ApiError } from '../../core/api/api-error';
import { SessionService } from '../../core/auth/session.service';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { AuthLayoutComponent } from './auth-layout.component';

/** Ingreso con correo y contraseña (RF-05, HU-01..HU-03). */
@Component({
  selector: 'app-login-page',
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
    <app-auth-layout title="Ingresa a tu cuenta">
      <form class="flex flex-col gap-5" [formGroup]="form" (ngSubmit)="submit()">
        @if (expired()) {
          <ui-alert tone="notice">Tu sesión terminó. Ingresa de nuevo para continuar.</ui-alert>
        }
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

        <ui-field label="Contraseña" for="password" [error]="passwordError()">
          <input
            uiInput
            id="password"
            type="password"
            formControlName="password"
            autocomplete="current-password"
            [invalid]="!!passwordError()"
            [attr.aria-describedby]="passwordError() ? 'password-msg' : null"
          />
        </ui-field>

        <ui-button type="submit" [full]="true" [loading]="submitting()">Ingresar</ui-button>
      </form>

      <p class="mt-6 text-center text-sm">
        <a routerLink="/recuperar" class="text-ink-muted underline hover:text-ink">
          ¿Olvidaste tu contraseña?
        </a>
      </p>

      <p class="mt-8 text-center text-sm leading-relaxed text-ink-muted">
        El registro es cerrado: solo se entra con una invitación del administrador.
      </p>
    </app-auth-layout>
  `,
})
export class LoginPage {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApi);
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly submitting = signal(false);
  protected readonly error = signal('');
  protected readonly submitted = signal(false);

  /** El interceptor manda aquí con `?expirada=1` cuando el refresco falla. */
  protected readonly expired = signal(
    this.route.snapshot.queryParamMap.has('expirada'),
  );

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  protected emailError(): string {
    const control = this.form.controls.email;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Escribe tu correo.';
    if (control.hasError('email')) return 'Ese correo no tiene un formato válido.';
    return '';
  }

  protected passwordError(): string {
    const control = this.form.controls.password;
    if (!this.submitted() && !(control.dirty && control.touched)) return '';
    return control.hasError('required') ? 'Escribe tu contraseña.' : '';
  }

  protected submit(): void {
    this.submitted.set(true);
    this.error.set('');
    if (this.form.invalid || this.submitting()) return;

    const { email, password } = this.form.getRawValue();
    this.submitting.set(true);

    this.authApi.login(email, password).subscribe({
      next: (tokens) => {
        this.session.adopt(tokens);
        const volverA = this.route.snapshot.queryParamMap.get('volverA');
        void this.router.navigateByUrl(volverA ?? '/inicio');
      },
      error: (err: ApiError) => {
        this.submitting.set(false);
        // El backend responde lo mismo ante credenciales incorrectas y ante
        // cuenta desactivada, para no revelar qué correos existen
        // (api-contract.md §1). Se muestra su mensaje tal cual.
        this.error.set(err.message);
      },
    });
  }
}
