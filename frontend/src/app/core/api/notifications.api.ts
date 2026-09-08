/**
 * Endpoints de notificaciones y de la configuración global (`api-contract.md` §7).
 *
 * La campana y la pantalla de administración son cosas distintas y comparten
 * este archivo porque comparten el prefijo del contrato, no porque se parezcan:
 * la primera la usa todo el mundo, la segunda solo un `ADMIN`.
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { AppNotification, NotificationSettings, Page } from './models';

export interface NotificationSettingsBody {
  reminder_days_before: number[];
  send_hour: number;
  overdue_enabled: boolean;
}

@Injectable({ providedIn: 'root' })
export class NotificationsApi {
  private readonly api = inject(ApiClient);

  list(unreadOnly = false, page = 1, size = 20): Observable<Page<AppNotification>> {
    return this.api.get<Page<AppNotification>>('/notifications', {
      // `false` viajaría como "false" y el backend lo leería como filtro puesto.
      unread_only: unreadOnly ? true : null,
      page,
      size,
    });
  }

  unreadCount(): Observable<{ unread: number }> {
    return this.api.get<{ unread: number }>('/notifications/unread-count');
  }

  markRead(id: string): Observable<AppNotification> {
    return this.api.post<AppNotification>(`/notifications/${id}/read`, {});
  }

  markAllRead(): Observable<{ marked: number }> {
    return this.api.post<{ marked: number }>('/notifications/read-all', {});
  }

  // --- Configuración global (solo ADMIN) ---

  settings(): Observable<NotificationSettings> {
    return this.api.get<NotificationSettings>('/admin/notification-settings');
  }

  saveSettings(body: NotificationSettingsBody): Observable<NotificationSettings> {
    return this.api.put<NotificationSettings>('/admin/notification-settings', body);
  }
}
