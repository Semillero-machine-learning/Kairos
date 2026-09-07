/**
 * Tipos del contrato de la API (`docs/api-contract.md`).
 *
 * Los nombres de campo son los que devuelve el backend, en inglés y en
 * `snake_case`: no se renombran al pasar por aquí, porque una capa de
 * traducción solo agrega un sitio más donde equivocarse.
 */

export type GlobalRole = 'ADMIN' | 'LESSON_EDITOR' | 'MEMBER';
export type UserStatus = 'ACTIVE' | 'DISABLED';
export type InvitationStatus = 'PENDING' | 'ACCEPTED' | 'REVOKED' | 'EXPIRED';

/** Etiquetas en español para lo que se muestra. */
export const GLOBAL_ROLE_LABEL: Record<GlobalRole, string> = {
  ADMIN: 'Administrador',
  LESSON_EDITOR: 'Editor de lecciones',
  MEMBER: 'Miembro',
};

export const USER_STATUS_LABEL: Record<UserStatus, string> = {
  ACTIVE: 'Activo',
  DISABLED: 'Desactivado',
};

export const INVITATION_STATUS_LABEL: Record<InvitationStatus, string> = {
  PENDING: 'Pendiente',
  ACCEPTED: 'Aceptada',
  REVOKED: 'Revocada',
  EXPIRED: 'Vencida',
};

/** Forma pública de un usuario, la que viaja dentro de la respuesta de ingreso. */
export interface User {
  id: string;
  full_name: string;
  email: string;
  global_role: GlobalRole;
}

/** Perfil completo del usuario en sesión (`GET /auth/me`). */
export interface Me extends User {
  status: UserStatus;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

/** Fila de `GET /users`. Quien no es administrador recibe solo id, nombre y
 * correo; el resto de campos llega nulo. */
export interface UserListItem {
  id: string;
  full_name: string;
  email: string;
  global_role: GlobalRole | null;
  status: UserStatus | null;
  created_at: string | null;
}

export interface UserDetail extends User {
  status: UserStatus;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface Invitation {
  id: string;
  email: string;
  global_role: GlobalRole;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
}

/** La respuesta de creación y reenvío incluye `invite_url`, que solo se
 * devuelve una vez: después solo queda el hash del token. */
export interface InvitationCreated {
  id: string;
  email: string;
  global_role: GlobalRole;
  status: InvitationStatus;
  expires_at: string;
  invite_url: string;
}
