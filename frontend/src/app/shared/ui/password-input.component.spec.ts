/**
 * El ojo de los campos de contraseña.
 *
 * Lo que se fija aquí es el contrato del control: que el `input` del
 * formulario siga siendo el del formulario —con su valor y su
 * `formControlName` intactos— y que alternar solo cambie lo que se ve.
 */
import { Component } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';

import { InputDirective } from './input.directive';
import { PasswordInputComponent } from './password-input.component';

@Component({
  imports: [ReactiveFormsModule, InputDirective, PasswordInputComponent],
  template: `
    <ui-password-input>
      <input uiInput [trailingSlot]="true" type="password" [formControl]="control" />
    </ui-password-input>
  `,
})
class HostComponent {
  readonly control = new FormControl('sin-mirar-atras', { nonNullable: true });
}

function setup() {
  const fixture = TestBed.createComponent(HostComponent);
  fixture.detectChanges();
  const root: HTMLElement = fixture.nativeElement;
  return {
    fixture,
    field: root.querySelector('input') as HTMLInputElement,
    button: root.querySelector('button') as HTMLButtonElement,
  };
}

describe('ui-password-input', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('arranca oculto y descubre la contraseña al pulsar', () => {
    const { fixture, field, button } = setup();

    expect(field.type).toBe('password');

    button.click();
    fixture.detectChanges();

    expect(field.type).toBe('text');
  });

  it('vuelve a ocultarla al pulsar de nuevo', () => {
    const { fixture, field, button } = setup();

    button.click();
    fixture.detectChanges();
    button.click();
    fixture.detectChanges();

    expect(field.type).toBe('password');
  });

  it('no toca el valor ni el control del formulario', () => {
    const { fixture, field } = setup();
    const host = fixture.componentInstance;

    fixture.nativeElement.querySelector('button').click();
    fixture.detectChanges();

    expect(field.value).toBe('sin-mirar-atras');
    expect(host.control.value).toBe('sin-mirar-atras');
  });

  it('anuncia la acción que hará, no el estado en el que está', () => {
    const { fixture, button } = setup();

    expect(button.getAttribute('aria-label')).toBe('Mostrar la contraseña');

    button.click();
    fixture.detectChanges();

    expect(button.getAttribute('aria-label')).toBe('Ocultar la contraseña');
  });

  it('no envía el formulario que lo contiene', () => {
    const { button } = setup();

    expect(button.type).toBe('button');
  });

  it('un clic no le quita el foco al campo', () => {
    const { field, button } = setup();

    field.focus();
    button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));

    expect(document.activeElement).toBe(field);
  });

  it('reserva sitio para el botón en el campo que envuelve', () => {
    const { field } = setup();

    expect(field.className).toContain('pr-11');
    expect(field.className).not.toContain('px-3');
  });
});
