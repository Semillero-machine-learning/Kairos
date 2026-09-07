/**
 * Endpoints de `/projects` y de sus miembros y roles (`api-contract.md` §3, §4).
 *
 * Aquí no se decide nada: qué puede hacer cada quien lo resuelve el backend en
 * cada petición. Lo único que hace este servicio es hablar HTTP.
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import {
  Page,
  Permission,
  PermissionCode,
  ProjectDetail,
  ProjectListItem,
  ProjectMember,
  ProjectRole,
  ProjectStatus,
} from './models';

export interface ProjectListFilters {
  status?: ProjectStatus | '';
  page?: number;
  size?: number;
}

export interface ProjectCreateBody {
  name: string;
  description: string | null;
  start_date: string | null;
  leader_user_id: string;
}

export interface ProjectUpdateBody {
  name?: string;
  description?: string | null;
  start_date?: string | null;
}

export interface RoleBody {
  name: string;
  color: string;
  permissions: PermissionCode[];
}

@Injectable({ providedIn: 'root' })
export class ProjectsApi {
  private readonly api = inject(ApiClient);

  // --- Proyectos ---

  list(filters: ProjectListFilters = {}): Observable<Page<ProjectListItem>> {
    return this.api.get<Page<ProjectListItem>>('/projects', { ...filters });
  }

  get(projectId: string): Observable<ProjectDetail> {
    return this.api.get<ProjectDetail>(`/projects/${projectId}`);
  }

  create(body: ProjectCreateBody): Observable<ProjectDetail> {
    return this.api.post<ProjectDetail>('/projects', body);
  }

  update(projectId: string, body: ProjectUpdateBody): Observable<ProjectDetail> {
    return this.api.patch<ProjectDetail>(`/projects/${projectId}`, body);
  }

  archive(projectId: string): Observable<ProjectDetail> {
    return this.api.post<ProjectDetail>(`/projects/${projectId}/archive`);
  }

  unarchive(projectId: string): Observable<ProjectDetail> {
    return this.api.post<ProjectDetail>(`/projects/${projectId}/unarchive`);
  }

  // --- Miembros ---

  members(projectId: string): Observable<ProjectMember[]> {
    return this.api.get<ProjectMember[]>(`/projects/${projectId}/members`);
  }

  addMember(projectId: string, userId: string, roleId: string): Observable<ProjectMember> {
    return this.api.post<ProjectMember>(`/projects/${projectId}/members`, {
      user_id: userId,
      project_role_id: roleId,
    });
  }

  removeMember(projectId: string, userId: string): Observable<void> {
    return this.api.delete<void>(`/projects/${projectId}/members/${userId}`);
  }

  changeMemberRole(
    projectId: string,
    userId: string,
    roleId: string,
  ): Observable<ProjectMember> {
    return this.api.patch<ProjectMember>(`/projects/${projectId}/members/${userId}/role`, {
      project_role_id: roleId,
    });
  }

  // --- Roles ---

  roles(projectId: string): Observable<ProjectRole[]> {
    return this.api.get<ProjectRole[]>(`/projects/${projectId}/roles`);
  }

  createRole(projectId: string, body: RoleBody): Observable<ProjectRole> {
    return this.api.post<ProjectRole>(`/projects/${projectId}/roles`, body);
  }

  updateRole(projectId: string, roleId: string, body: RoleBody): Observable<ProjectRole> {
    return this.api.patch<ProjectRole>(`/projects/${projectId}/roles/${roleId}`, body);
  }

  deleteRole(projectId: string, roleId: string): Observable<void> {
    return this.api.delete<void>(`/projects/${projectId}/roles/${roleId}`);
  }

  // --- Catálogo ---

  permissions(): Observable<Permission[]> {
    return this.api.get<Permission[]>('/permissions');
  }
}
