/**
 * HU-14 — Arranque en frío (RNF-02, EB-13).
 *
 * El escenario de `docs/user-stories.md` se prueba aquí y no en el navegador
 * porque los umbrales son 3 y 90 segundos: con relojes falsos se comprueban
 * exactos, y esperarlos de verdad no probaría nada más.
 *
 * Lo que se fija:
 *  - nada antes de los 3 s, aviso a partir de los 3 s;
 *  - la petición sigue viva mientras tanto, no se cancela ni se reemplaza;
 *  - a los 90 s se corta con `TimeoutError`, que la interfaz traduce a un
 *    mensaje honesto en español, nunca a un error genérico;
 *  - y el aviso se apaga al terminar la petición, tanto si respondió como si
 *    se le acabó el tiempo. Un aviso pegado diría que el servidor sigue
 *    despertando cuando ya se sabe que no.
 */
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, CLIENT_ERROR_CODES, TimeoutError, toApiError } from '../api/api-error';
import { coldStartInterceptor } from './cold-start.interceptor';
import { REQUEST_TIMEOUT_MS, SLOW_REQUEST_MS, ColdStartService } from './cold-start.service';

describe('coldStartInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let coldStart: ColdStartService;

  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([coldStartInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    coldStart = TestBed.inject(ColdStartService);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('no avisa nada antes de los 3 segundos', () => {
    http.get('/api/v1/projects').subscribe({ error: () => undefined });
    httpMock.expectOne('/api/v1/projects');

    vi.advanceTimersByTime(SLOW_REQUEST_MS - 1);

    expect(coldStart.waking()).toBe(false);
  });

  it('avisa que el servidor está despertando pasados los 3 segundos', () => {
    http.get('/api/v1/projects').subscribe({ error: () => undefined });
    const pendiente = httpMock.expectOne('/api/v1/projects');

    vi.advanceTimersByTime(SLOW_REQUEST_MS);

    expect(coldStart.waking()).toBe(true);
    // Y la petición sigue en pie: avisar no es rendirse.
    expect(pendiente.cancelled).toBe(false);
  });

  it('apaga el aviso cuando el servidor por fin responde', () => {
    let recibido: unknown = null;
    http.get('/api/v1/projects').subscribe((body) => (recibido = body));
    const pendiente = httpMock.expectOne('/api/v1/projects');

    vi.advanceTimersByTime(SLOW_REQUEST_MS);
    expect(coldStart.waking()).toBe(true);

    pendiente.flush({ items: [] });

    expect(recibido).toEqual({ items: [] });
    expect(coldStart.waking()).toBe(false);
  });

  it('a los 90 segundos corta con un mensaje honesto, no con un error genérico', () => {
    let capturado: unknown = null;
    http.get('/api/v1/projects').subscribe({ error: (error) => (capturado = error) });
    httpMock.expectOne('/api/v1/projects');

    vi.advanceTimersByTime(REQUEST_TIMEOUT_MS);

    expect(capturado).toBeInstanceOf(TimeoutError);

    // Lo que acaba viendo el usuario: español, y explicando qué pasó.
    const mostrado = toApiError(capturado);
    expect(mostrado).toBeInstanceOf(ApiError);
    expect(mostrado.code).toBe(CLIENT_ERROR_CODES.TIMEOUT);
    expect(mostrado.message).toMatch(/tardó demasiado/i);
  });

  it('apaga el aviso también cuando se acaba el tiempo de espera', () => {
    http.get('/api/v1/projects').subscribe({ error: () => undefined });
    httpMock.expectOne('/api/v1/projects');

    vi.advanceTimersByTime(REQUEST_TIMEOUT_MS);

    // Si esto quedara encendido, la interfaz diría «Despertando el servidor...»
    // encima del mensaje de que el servidor no respondió.
    expect(coldStart.waking()).toBe(false);
  });

  it('sigue avisando mientras quede una petición lenta, aunque otra ya haya vuelto', () => {
    http.get('/api/v1/projects').subscribe({ error: () => undefined });
    http.get('/api/v1/notifications').subscribe({ error: () => undefined });
    const proyectos = httpMock.expectOne('/api/v1/projects');
    httpMock.expectOne('/api/v1/notifications');

    vi.advanceTimersByTime(SLOW_REQUEST_MS);
    expect(coldStart.waking()).toBe(true);

    proyectos.flush({ items: [] });

    // La de notificaciones sigue en vuelo: el servidor sigue despertando.
    expect(coldStart.waking()).toBe(true);
  });
});
