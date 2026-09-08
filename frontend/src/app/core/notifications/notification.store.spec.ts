import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SessionService } from '../auth/session.service';
import { NotificationStore } from './notification.store';

/** Sesión abierta, que es la única condición que la tienda consulta. */
const sessionStub = { isAuthenticated: () => true } as unknown as SessionService;

const unaNotificacion = (id: string, readAt: string | null = null) => ({
  id,
  kind: 'TASK_ASSIGNED' as const,
  title: 'Te asignaron una tarea',
  body: 'Ahora eres responsable de «Entrenar el modelo».',
  task_id: 't1',
  project_id: 'p1',
  read_at: readAt,
  created_at: '2026-09-08T12:00:00Z',
});

describe('NotificationStore', () => {
  let store: NotificationStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SessionService, useValue: sessionStub },
      ],
    });
    store = TestBed.inject(NotificationStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    store.stop();
    http.verify();
  });

  it('empieza en cero y sin historial', () => {
    expect(store.unread()).toBe(0);
    expect(store.items()).toEqual([]);
  });

  it('un fallo del contador no borra el número que ya se veía', () => {
    store.refreshCount();
    http.expectOne((r) => r.url.endsWith('/notifications/unread-count')).flush({ unread: 4 });
    expect(store.unread()).toBe(4);

    store.refreshCount();
    http
      .expectOne((r) => r.url.endsWith('/notifications/unread-count'))
      .flush({}, { status: 503, statusText: 'Service Unavailable' });

    // El siguiente sondeo lo corregirá; mientras tanto, un 4 viejo informa más
    // que un 0 falso.
    expect(store.unread()).toBe(4);
    expect(store.error()).toBe('');
  });

  it('marcar una como leída vuelve a pedir el contador', () => {
    store.loadHistory();
    http
      .expectOne((r) => r.url.endsWith('/notifications'))
      .flush({ items: [unaNotificacion('n1')], total: 1, page: 1, size: 20 });

    store.markRead('n1');
    http
      .expectOne((r) => r.url.endsWith('/notifications/n1/read'))
      .flush(unaNotificacion('n1', '2026-09-08T13:00:00Z'));

    expect(store.items()[0].read_at).not.toBeNull();
    http.expectOne((r) => r.url.endsWith('/notifications/unread-count')).flush({ unread: 0 });
    expect(store.unread()).toBe(0);
  });

  it('no vuelve a marcar una notificación ya leída', () => {
    store.loadHistory();
    http
      .expectOne((r) => r.url.endsWith('/notifications'))
      .flush({
        items: [unaNotificacion('n1', '2026-09-08T13:00:00Z')],
        total: 1,
        page: 1,
        size: 20,
      });

    store.markRead('n1');

    // Ninguna petición: `http.verify()` del afterEach lo confirma.
    expect(store.items()[0].read_at).toBe('2026-09-08T13:00:00Z');
  });

  it('marcar todas deja el contador en cero sin releer la lista', () => {
    store.loadHistory();
    http
      .expectOne((r) => r.url.endsWith('/notifications'))
      .flush({
        items: [unaNotificacion('n1'), unaNotificacion('n2')],
        total: 2,
        page: 1,
        size: 20,
      });

    store.markAllRead();
    http.expectOne((r) => r.url.endsWith('/notifications/read-all')).flush({ marked: 2 });

    expect(store.unread()).toBe(0);
    expect(store.items().every((item) => item.read_at !== null)).toBe(true);
  });

  it('el sondeo no se duplica si se arranca dos veces', () => {
    vi.useFakeTimers();
    store.start();
    store.start();
    http.expectOne((r) => r.url.endsWith('/notifications/unread-count')).flush({ unread: 1 });

    vi.advanceTimersByTime(60_000);
    // Un solo temporizador, así que una sola petición.
    http.expectOne((r) => r.url.endsWith('/notifications/unread-count')).flush({ unread: 1 });

    store.stop();
    vi.advanceTimersByTime(120_000);
    vi.useRealTimers();
  });

  it('reset deja la campana como recién abierta', () => {
    store.refreshCount();
    http.expectOne((r) => r.url.endsWith('/notifications/unread-count')).flush({ unread: 7 });

    store.reset();

    expect(store.unread()).toBe(0);
    expect(store.items()).toEqual([]);
  });
});
