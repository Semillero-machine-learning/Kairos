/** Endpoints de `/users` (api-contract.md §2). Todo exige rol global ADMIN
 * salvo la lista, que cualquier autenticado consulta en versión reducida. */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { GlobalRole, Page, UserDetail, UserListItem, UserStatus } from './models';

export interface UserListFilters {
  search?: string;
  status?: UserStatus | '';
  global_role?: GlobalRole | '';
  page?: number;
  size?: number;
}

@Injectable({ providedIn: 'root' })
export class UsersApi {
  private readonly api = inject(ApiClient);

  list(filters: UserListFilters = {}): Observable<Page<UserListItem>> {
    return this.api.get<Page<UserListItem>>('/users', { ...filters });
  }

  get(userId: string): Observable<UserDetail> {
    return this.api.get<UserDetail>(`/users/${userId}`);
  }

  changeRole(userId: string, globalRole: GlobalRole): Observable<UserDetail> {
    return this.api.patch<UserDetail>(`/users/${userId}/role`, { global_role: globalRole });
  }

  changeStatus(userId: string, status: UserStatus): Observable<UserDetail> {
    return this.api.patch<UserDetail>(`/users/${userId}/status`, { status });
  }
}
