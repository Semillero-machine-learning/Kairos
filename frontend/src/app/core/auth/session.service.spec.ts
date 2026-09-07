import { HttpClient, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';

import { TokenResponse } from '../api/models';
import { SessionService } from './session.service';
import { tokenStorage } from './token-storage';

const API = 'http://localhost:8000/api/v1';

function tokens(suffix: string): TokenResponse {
  return {
    access_token: `access-${suffix}`,
    refresh_token: `refresh-${suffix}`,
    token_type: 'bearer',
    expires_in: 900,
    user: {
      id: 'u1',
      full_name: 'Ana Gómez',
      email: 'ana@ejemplo.com',
      global_role: 'MEMBER',
    },
  };
}

describe('SessionService', () => {
  let session: SessionService;
  let http: HttpTestingController;

  beforeEach(() => {
    tokenStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    session = TestBed.inject(SessionService);
    http = TestBed.inject(HttpTestingController);
  });

  it('adopta la sesión que devuelve el ingreso y expone el rol global', () => {
    session.adopt({ ...tokens('1'), user: { ...tokens('1').user, global_role: 'ADMIN' } });

    expect(session.isAuthenticated()).toBe(true);
    expect(session.isAdmin()).toBe(true);
    expect(session.accessToken()).toBe('access-1');
  });

  /**
   * El backend rota el token de refresco en cada uso (RN-43): si dos peticiones
   * que reciben 401 a la vez disparan cada una su refresco, la segunda usa un
   * token que la primera ya invalidó y la sesión se cae sin motivo.
   */
  it('comparte un único refresco entre llamadas concurrentes', async () => {
    session.adopt(tokens('1'));

    // `refresh()` es frío: la petición sale al suscribirse, no al llamarlo.
    const resultados = Promise.all([
      new Promise<string>((resolve) => session.refresh().subscribe(resolve)),
      new Promise<string>((resolve) => session.refresh().subscribe(resolve)),
    ]);

    // Un solo refresco en vuelo, aunque se hayan pedido dos.
    const pendiente = http.expectOne(`${API}/auth/refresh`);
    expect(pendiente.request.body).toEqual({ refresh_token: 'refresh-1' });

    pendiente.flush(tokens('2'));

    expect(await resultados).toEqual(['access-2', 'access-2']);
    // Y el token rotado queda guardado para el siguiente refresco.
    expect(session.accessToken()).toBe('access-2');
    http.verify();
  });

  it('permite un refresco nuevo después de que el anterior terminó', async () => {
    session.adopt(tokens('1'));

    const primero = new Promise<string>((resolve) => session.refresh().subscribe(resolve));
    http.expectOne(`${API}/auth/refresh`).flush(tokens('2'));
    await primero;

    const segundo = new Promise<string>((resolve) => session.refresh().subscribe(resolve));
    const peticion = http.expectOne(`${API}/auth/refresh`);
    // Usa el token rotado, no el original.
    expect(peticion.request.body).toEqual({ refresh_token: 'refresh-2' });
    peticion.flush(tokens('3'));

    expect(await segundo).toBe('access-3');
    http.verify();
  });

  it('cierra la sesión local aunque la revocación en el servidor falle', async () => {
    session.adopt(tokens('1'));

    const salida = new Promise<void>((resolve) => session.logout().subscribe(() => resolve()));
    http.expectOne(`${API}/auth/logout`).error(new ProgressEvent('error'), { status: 500 });
    await salida;

    expect(session.isAuthenticated()).toBe(false);
    expect(session.accessToken()).toBeNull();
    expect(tokenStorage.load()).toBeNull();
  });

  it('sin tokens guardados no intenta restaurar nada', async () => {
    const restaurada = await new Promise<boolean>((resolve) =>
      session.restore().subscribe(resolve),
    );

    expect(restaurada).toBe(false);
    expect(session.restoring()).toBe(false);
    http.verify();
  });
});
