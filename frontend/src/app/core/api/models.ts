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

// --- Proyectos, roles y permisos (api-contract.md §3 y §4) ---

export type ProjectStatus = 'ACTIVE' | 'ARCHIVED';

export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
  ACTIVE: 'Activo',
  ARCHIVED: 'Archivado',
};

/**
 * Los 14 códigos del catálogo cerrado (`business-rules.md` §3).
 *
 * El tipo se declara aquí para que un permiso mal escrito falle al compilar,
 * pero la lista que se muestra en el editor de roles viene siempre de
 * `GET /permissions`: el backend es la fuente de verdad.
 */
export type PermissionCode =
  | 'task.view'
  | 'task.comment'
  | 'task.create'
  | 'task.edit_any'
  | 'task.delete'
  | 'task.assign'
  | 'task.change_status_any'
  | 'task.review'
  | 'member.add'
  | 'member.remove'
  | 'role.assign'
  | 'role.manage'
  | 'project.edit'
  | 'project.archive';

/** Obligatorio en todo rol (RN-05). */
export const VIEW_PERMISSION: PermissionCode = 'task.view';

export type PermissionCategory = 'task' | 'member' | 'role' | 'project';

export const PERMISSION_CATEGORY_LABEL: Record<PermissionCategory, string> = {
  task: 'Tareas',
  member: 'Miembros',
  role: 'Roles',
  project: 'Proyecto',
};

export interface Permission {
  code: PermissionCode;
  description: string;
  category: PermissionCategory;
}

export interface UserRef {
  id: string;
  full_name: string;
  email: string;
}

export interface ProjectRoleRef {
  id: string;
  name: string;
  color: string;
}

export interface ProjectListItem {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  start_date: string | null;
  member_count: number;
  /** Nulo cuando un administrador mira un proyecto del que no es miembro. */
  my_role: ProjectRoleRef | null;
  created_at: string;
}

export type TaskCounts = Record<'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'IN_REVIEW' | 'DONE', number>;

export interface ProjectDetail {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  start_date: string | null;
  archived_at: string | null;
  member_count: number;
  /** Todo en cero hasta la Fase 3, cuando exista el módulo de tareas. */
  task_counts: TaskCounts;
  my_permissions: PermissionCode[];
  my_role: ProjectRoleRef | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  user: UserRef;
  role: ProjectRoleRef;
  joined_at: string;
}

export interface ProjectRole {
  id: string;
  project_id: string;
  name: string;
  color: string;
  is_system: boolean;
  permissions: PermissionCode[];
  /** Quién creó el rol (RN-19). Nulo en los tres del sistema. */
  created_by: UserRef | null;
  member_count: number;
  created_at: string;
}

// --- Tareas (api-contract.md §5 y §6) ---

export type TaskStatus = 'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'IN_REVIEW' | 'DONE';

/** El orden del tablero, de izquierda a derecha (RF-28). */
export const TASK_STATUS_ORDER: readonly TaskStatus[] = [
  'BACKLOG',
  'TODO',
  'IN_PROGRESS',
  'IN_REVIEW',
  'DONE',
] as const;

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  BACKLOG: 'Por planear',
  TODO: 'Por hacer',
  IN_PROGRESS: 'En progreso',
  IN_REVIEW: 'En revisión',
  DONE: 'Hecha',
};

export type TaskPeriodicity = 'ONE_TIME' | 'WEEKLY' | 'MONTHLY' | 'SEMESTER';

/** Los nombres son los del RF-26. La periodicidad es una etiqueta descriptiva:
 * no genera ninguna tarea. */
export const TASK_PERIODICITY_LABEL: Record<TaskPeriodicity, string> = {
  ONE_TIME: 'Puntual',
  WEEKLY: 'Semanal',
  MONTHLY: 'Mensual',
  SEMESTER: 'Semestral',
};

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  periodicity: TaskPeriodicity;
  due_date: string | null;
  /** Lo calcula el backend contra la fecha de Bogotá: la insignia de la tarjeta
   * y el filtro «vencidas» no pueden discrepar. */
  is_overdue: boolean;
  assignees: UserRef[];
  created_by: UserRef;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Una fila de «Mis tareas»: la tarea con el proyecto del que viene (RF-36). */
export interface MyTask extends Task {
  project: { id: string; name: string };
}

export type SubmissionReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export const SUBMISSION_STATUS_LABEL: Record<SubmissionReviewStatus, string> = {
  PENDING: 'Sin revisar',
  APPROVED: 'Aprobada',
  REJECTED: 'Devuelta',
};

export interface Submission {
  id: string;
  task_id: string;
  submitted_by: UserRef;
  description: string;
  commit_url: string | null;
  review_status: SubmissionReviewStatus;
  reviewed_by: UserRef | null;
  reviewed_at: string | null;
  review_comment: string | null;
  created_at: string;
}
