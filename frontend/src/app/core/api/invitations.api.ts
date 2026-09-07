/** Endpoints de `/invitations` (api-contract.md §2). Todos exigen rol global
 * ADMIN; el backend lo verifica, aquí solo se consume. */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { GlobalRole, Invitation, InvitationCreated, InvitationStatus } from './models';

@Injectable({ providedIn: 'root' })
export class InvitationsApi {
  private readonly api = inject(ApiClient);

  list(status?: InvitationStatus | ''): Observable<Invitation[]> {
    return this.api.get<Invitation[]>('/invitations', { status });
  }

  create(email: string, globalRole: GlobalRole): Observable<InvitationCreated> {
    return this.api.post<InvitationCreated>('/invitations', {
      email,
      global_role: globalRole,
    });
  }

  /** Reenviar invalida el token anterior y genera uno nuevo (RF-04). */
  resend(invitationId: string): Observable<InvitationCreated> {
    return this.api.post<InvitationCreated>(`/invitations/${invitationId}/resend`);
  }

  revoke(invitationId: string): Observable<void> {
    return this.api.delete<void>(`/invitations/${invitationId}`);
  }
}
