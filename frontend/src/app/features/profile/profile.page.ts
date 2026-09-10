import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import { AuthApi } from '../../core/api/auth.api';
import { GLOBAL_ROLE_LABEL } from '../../core/api/models';
import { PASSWORD_HINT, PASSWORD_MIN_LENGTH, PASSWORD_TOO_SHORT } from '../../core/auth/password';
import { SessionService } from '../../core/auth/session.service';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { PasswordInputComponent } from '../../shared/ui/password-input.component';

/** Perfil propio: editar el nombre y cambiar la contraseña (RF-08, RN-42). */
@Component({
  selector: 'app-profile-page',
  imports: [
    ReactiveFormsModule,
    PageHeaderComponent,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
    PasswordInputComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-2xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header title="Mi perfil" />

      <section class="mt-8" aria-labelledby="datos">
        <h2 id="datos" class="text-sm font-medium text-ink">Datos de la cuenta</h2>

        <dl class="mt-3 flex flex-col gap-3 text-sm">
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <dt class="w-28 shrink-0 text-ink-muted">Correo</dt>
            <dd class="text-ink">{{ session.user()?.email }}</dd>
          </div>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <dt class="w-28 shrink-0 text-ink-muted">Rol global</dt>
            <dd>
              <ui-badge tone="accent">{{ roleLabel() }}</ui-badge>
            </dd>
          </div>
        </dl>
        <p class="mt-3 text-sm text-ink-muted">
          El correo y el rol global solo los cambia un administrador.
        </p>
      </section>

      <section class="mt-10 border-t border-line pt-8" aria-labelledby="nombre">
        <h2 id="nombre" class="text-sm font-medium text-ink">Nombre</h2>
        <form class="mt-4 flex flex-col gap-4" [formGroup]="nameForm" (ngSubmit)="saveName()">
          @if (nameError()) {
            <ui-alert tone="error">{{ nameError() }}</ui-alert>
          }
          @if (nameSaved()) {
            <ui-alert tone="success">Tu nombre quedó actualizado.</ui-alert>
          }

          <ui-field label="Nombre completo" for="fullName" [error]="fullNameFieldError()">
            <input
              uiInput
              id="fullName"
              type="text"
              formControlName="fullName"
              autocomplete="name"
              [invalid]="!!fullNameFieldError()"
              [attr.aria-describedby]="fullNameFieldError() ? 'fullName-msg' : null"
            />
          </ui-field>

          <div>
            <ui-button type="submit" [loading]="savingName()">Guardar el nombre</ui-button>
          </div>
        </form>
      </section>

      <section class="mt-10 border-t border-line pt-8" aria-labelledby="contrasena">
        <h2 id="contrasena" class="text-sm font-medium text-ink">Contraseña</h2>
        <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">
          Al cambiarla se cerrarán todas tus otras sesiones.
        </p>

        <form
          class="mt-4 flex flex-col gap-4"
          [formGroup]="passwordForm"
          (ngSubmit)="savePassword()"
        >
          @if (passwordError()) {
            <ui-alert tone="error">{{ passwordError() }}</ui-alert>
          }
          @if (passwordSaved()) {
            <ui-alert tone="success">Tu contraseña quedó cambiada.</ui-alert>
          }

          <ui-field label="Contraseña actual" for="current" [error]="currentFieldError()">
            <ui-password-input>
              <input
                uiInput
                [trailingSlot]="true"
                id="current"
                type="password"
                formControlName="currentPassword"
                autocomplete="current-password"
                [invalid]="!!currentFieldError()"
                [attr.aria-describedby]="currentFieldError() ? 'current-msg' : null"
              />
            </ui-password-input>
          </ui-field>

          <ui-field
            label="Contraseña nueva"
            for="new"
            [hint]="passwordHint"
            [error]="newFieldError()"
          >
            <ui-password-input>
              <input
                uiInput
                [trailingSlot]="true"
                id="new"
                type="password"
                formControlName="newPassword"
                autocomplete="new-password"
                [invalid]="!!newFieldError()"
                aria-describedby="new-msg"
              />
            </ui-password-input>
          </ui-field>

          <div>
            <ui-button type="submit" [loading]="savingPassword()">Cambiar la contraseña</ui-button>
          </div>
        </form>
      </section>
    </div>
  `,
})
export class ProfilePage {
  protected readonly session = inject(SessionService);
  private readonly authApi = inject(AuthApi);
  private readonly fb = inject(FormBuilder);

  protected readonly passwordHint = PASSWORD_HINT;

  protected readonly savingName = signal(false);
  protected readonly nameSaved = signal(false);
  protected readonly nameError = signal('');
  protected readonly nameSubmitted = signal(false);

  protected readonly savingPassword = signal(false);
  protected readonly passwordSaved = signal(false);
  protected readonly passwordError = signal('');
  protected readonly passwordSubmitted = signal(false);

  protected readonly nameForm = this.fb.nonNullable.group({
    fullName: [
      this.session.user()?.full_name ?? '',
      [Validators.required, Validators.minLength(2), Validators.maxLength(120)],
    ],
  });

  protected readonly passwordForm = this.fb.nonNullable.group({
    currentPassword: ['', [Validators.required]],
    newPassword: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]],
  });

  protected roleLabel(): string {
    const role = this.session.user()?.global_role;
    return role ? GLOBAL_ROLE_LABEL[role] : '';
  }

  protected fullNameFieldError(): string {
    const control = this.nameForm.controls.fullName;
    if (!this.nameSubmitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Escribe tu nombre completo.';
    if (control.hasError('minlength')) return 'El nombre debe tener al menos 2 caracteres.';
    if (control.hasError('maxlength')) return 'El nombre no puede pasar de 120 caracteres.';
    return '';
  }

  protected currentFieldError(): string {
    const control = this.passwordForm.controls.currentPassword;
    if (!this.passwordSubmitted() && !(control.dirty && control.touched)) return '';
    return control.hasError('required') ? 'Escribe tu contraseña actual.' : '';
  }

  protected newFieldError(): string {
    const control = this.passwordForm.controls.newPassword;
    if (!this.passwordSubmitted() && !(control.dirty && control.touched)) return '';
    if (control.hasError('required')) return 'Define la contraseña nueva.';
    if (control.hasError('minlength')) return PASSWORD_TOO_SHORT;
    return '';
  }

  protected saveName(): void {
    this.nameSubmitted.set(true);
    this.nameError.set('');
    this.nameSaved.set(false);
    if (this.nameForm.invalid || this.savingName()) return;

    this.savingName.set(true);
    this.authApi.updateMe(this.nameForm.getRawValue().fullName).subscribe({
      next: (me) => {
        this.savingName.set(false);
        this.nameSaved.set(true);
        this.session.patchUser(me);
      },
      error: (err: ApiError) => {
        this.savingName.set(false);
        this.nameError.set(err.message);
      },
    });
  }

  protected savePassword(): void {
    this.passwordSubmitted.set(true);
    this.passwordError.set('');
    this.passwordSaved.set(false);
    if (this.passwordForm.invalid || this.savingPassword()) return;

    const { currentPassword, newPassword } = this.passwordForm.getRawValue();
    this.savingPassword.set(true);

    this.authApi.changePassword(currentPassword, newPassword).subscribe({
      next: () => {
        this.savingPassword.set(false);
        this.passwordSaved.set(true);
        this.passwordSubmitted.set(false);
        this.passwordForm.reset();
      },
      error: (err: ApiError) => {
        this.savingPassword.set(false);
        this.passwordError.set(err.message);
      },
    });
  }
}
