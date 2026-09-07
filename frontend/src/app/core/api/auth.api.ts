/** Endpoints de `/auth` (api-contract.md §1). */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { Me, TokenResponse } from './models';

@Injectable({ providedIn: 'root' })
export class AuthApi {
  private readonly api = inject(ApiClient);

  login(email: string, password: string): Observable<TokenResponse> {
    return this.api.post<TokenResponse>('/auth/login', { email, password });
  }

  refresh(refreshToken: string): Observable<TokenResponse> {
    return this.api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken });
  }

  logout(refreshToken: string): Observable<void> {
    return this.api.post<void>('/auth/logout', { refresh_token: refreshToken });
  }

  me(): Observable<Me> {
    return this.api.get<Me>('/auth/me');
  }

  updateMe(fullName: string): Observable<Me> {
    return this.api.patch<Me>('/auth/me', { full_name: fullName });
  }

  changePassword(currentPassword: string, newPassword: string): Observable<void> {
    return this.api.post<void>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  /** Valida el token de invitación y devuelve el correo asociado, que el
   * formulario de aceptación muestra precargado y no editable (HU-02). */
  invitationInfo(token: string): Observable<{ email: string }> {
    return this.api.get<{ email: string }>(`/auth/invitations/${encodeURIComponent(token)}`);
  }

  acceptInvitation(token: string, fullName: string, password: string): Observable<TokenResponse> {
    return this.api.post<TokenResponse>(
      `/auth/invitations/${encodeURIComponent(token)}/accept`,
      { full_name: fullName, password },
    );
  }

  /** Responde siempre igual, exista o no la cuenta (RN-41). */
  requestPasswordReset(email: string): Observable<{ message: string }> {
    return this.api.post<{ message: string }>('/auth/password-reset/request', { email });
  }

  confirmPasswordReset(token: string, newPassword: string): Observable<void> {
    return this.api.post<void>('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    });
  }
}
