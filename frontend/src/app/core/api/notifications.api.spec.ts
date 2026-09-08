import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { NotificationsApi } from './notifications.api';

describe('NotificationsApi', () => {
  let api: NotificationsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(NotificationsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('no manda unread_only cuando está apagado', () => {
    api.list(false).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/notifications'));
    // `unread_only=false` viajaría como la cadena "false", que el backend
    // leería como un filtro puesto.
    expect(request.request.params.has('unread_only')).toBe(false);
    request.flush({ items: [], total: 0, page: 1, size: 20 });
  });

  it('manda unread_only cuando se pide solo lo no leído', () => {
    api.list(true).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/notifications'));
    expect(request.request.params.get('unread_only')).toBe('true');
    request.flush({ items: [], total: 0, page: 1, size: 20 });
  });

  it('el contador cuelga de su propia ruta', () => {
    api.unreadCount().subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/notifications/unread-count'));
    expect(request.request.method).toBe('GET');
    request.flush({ unread: 3 });
  });

  it('marcar como leída es un POST sin cuerpo significativo', () => {
    api.markRead('n1').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/notifications/n1/read'));
    expect(request.request.method).toBe('POST');
    request.flush({});
  });

  it('la configuración global va por PUT y sin zona horaria', () => {
    api
      .saveSettings({ reminder_days_before: [3, 1], send_hour: 8, overdue_enabled: true })
      .subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/admin/notification-settings'));
    expect(request.request.method).toBe('PUT');
    // RN-26 fija la zona horaria: mandarla sería sugerir que se puede cambiar.
    expect(request.request.body).toEqual({
      reminder_days_before: [3, 1],
      send_hour: 8,
      overdue_enabled: true,
    });
    request.flush({});
  });
});
