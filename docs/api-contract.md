# Contrato de la API

Base: `https://api.kairospartners.uk/api/v1`
Autenticación: `Authorization: Bearer <access_token>` salvo donde se indique lo contrario.
Todas las respuestas son JSON. Los errores siguen el formato de `architecture.md`, sección 7.

**Convenciones:** listas paginadas con `?page=1&size=20`, devolviendo `{ "items": [...], "total": n, "page": p, "size": s }`. Los identificadores son UUID. Las fechas de vencimiento son `YYYY-MM-DD`; el resto de marcas de tiempo son ISO 8601 en UTC.

---

## 1. Autenticación — `/auth`

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| POST | `/auth/login` | Pública | Ingreso con correo y contraseña |
| POST | `/auth/refresh` | Pública | Renueva tokens (rotación) |
| POST | `/auth/logout` | Requerida | Revoca el token de refresco |
| GET | `/auth/me` | Requerida | Perfil del usuario en sesión |
| PATCH | `/auth/me` | Requerida | Edita el nombre propio |
| POST | `/auth/change-password` | Requerida | Cambia la contraseña con la actual |
| GET | `/auth/invitations/{token}` | Pública | Valida un token de invitación y devuelve el correo asociado |
| POST | `/auth/invitations/{token}/accept` | Pública | Crea la cuenta |
| POST | `/auth/password-reset/request` | Pública | Solicita el enlace de restablecimiento |
| POST | `/auth/password-reset/confirm` | Pública | Define la nueva contraseña con el token |

**POST `/auth/login`**
```json
// petición
{ "email": "ana@ejemplo.com", "password": "..." }

// 200
{
  "access_token": "eyJ...",
  "refresh_token": "a1b2...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": "...", "full_name": "Ana Gómez", "email": "...", "global_role": "MEMBER" }
}
```
Errores: `401 UNAUTHENTICATED` con credenciales incorrectas o cuenta desactivada. **El mensaje es idéntico en ambos casos**, para no revelar qué correos existen.

**POST `/auth/invitations/{token}/accept`**
```json
{ "full_name": "Ana Gómez", "password": "unaClaveLarga" }
```
Errores: `404` token inexistente, `409 INVITATION_EXPIRED`, `409 INVITATION_ALREADY_USED`.

**POST `/auth/password-reset/request`** devuelve siempre `202 Accepted` con el mismo cuerpo, exista o no la cuenta (RN-41).

---

## 2. Usuarios e invitaciones — `/users`, `/invitations`

Todo este grupo exige rol global `ADMIN`, salvo `GET /users` que cualquier autenticado puede consultar en versión reducida (solo id, nombre y correo) para los selectores de asignación.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/users` | Lista con `?search=&status=&global_role=` |
| GET | `/users/{id}` | Detalle |
| PATCH | `/users/{id}/role` | Cambia el rol global |
| PATCH | `/users/{id}/status` | Activa o desactiva |
| GET | `/invitations` | Lista con `?status=` |
| POST | `/invitations` | Crea y envía la invitación |
| POST | `/invitations/{id}/resend` | Reenvía, invalidando el token anterior |
| DELETE | `/invitations/{id}` | Revoca una invitación pendiente |

**POST `/invitations`**
```json
// petición
{ "email": "nuevo@ejemplo.com", "global_role": "MEMBER" }

// 201
{
  "id": "...",
  "email": "nuevo@ejemplo.com",
  "global_role": "MEMBER",
  "status": "PENDING",
  "expires_at": "2026-09-12T14:00:00Z",
  "invite_url": "https://app.kairospartners.uk/invitacion/a1b2c3..."
}
```
`invite_url` se devuelve **una sola vez**, para que el administrador pueda copiarla y enviarla por otro canal. Después no se puede recuperar: solo se guarda el hash del token.

Errores: `409 EMAIL_ALREADY_REGISTERED`, `409 LAST_ADMIN` al intentar degradar o desactivar al último administrador.

---

## 3. Proyectos — `/projects`

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/projects` | Autenticado. Devuelve los proyectos del usuario; un `ADMIN` ve todos. Filtro `?status=` |
| POST | `/projects` | Rol global `ADMIN` |
| GET | `/projects/{id}` | `task.view` |
| PATCH | `/projects/{id}` | `project.edit` |
| POST | `/projects/{id}/archive` | `project.archive` |
| POST | `/projects/{id}/unarchive` | `project.archive` |

**POST `/projects`**
```json
{
  "name": "Detección de anomalías",
  "description": "...",
  "start_date": "2026-09-10",
  "leader_user_id": "uuid-de-carlos"
}
```
En una sola transacción: crea el proyecto, genera los tres roles predeterminados con sus permisos, y agrega al líder designado.

**GET `/projects/{id}`** incluye `my_permissions`, el arreglo de códigos de permiso del usuario en ese proyecto, para que el frontend sepa qué mostrar:
```json
{
  "id": "...",
  "name": "Detección de anomalías",
  "status": "ACTIVE",
  "member_count": 5,
  "task_counts": { "BACKLOG": 3, "TODO": 4, "IN_PROGRESS": 2, "IN_REVIEW": 1, "DONE": 12 },
  "my_permissions": ["task.view", "task.comment", "task.create", "..."]
}
```

---

`task_counts` se calcula al consultar, sin columnas de conteo, y no incluye las tareas con borrado lógico.

Un proyecto **archivado** sigue respondiendo a las lecturas (`task.view`), tal como manda RF-18: solo se rechazan las escrituras, con `409 PROJECT_ARCHIVED`. La única escritura que se permite es desarchivar. Archivar un proyecto ya archivado, o desarchivar uno activo, devuelve `409`.

El rol global `ADMIN` que **no** es miembro de un proyecto obtiene `task.view`, `member.add` y `role.assign`: lectura universal para supervisar (RN-01) más lo justo para reasignar el liderazgo, que RN-14 le garantiza siempre. No obtiene ningún permiso de trabajo sobre tareas.

---

## 4. Miembros y roles de proyecto

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/projects/{id}/members` | `task.view` |
| POST | `/projects/{id}/members` | `member.add` |
| DELETE | `/projects/{id}/members/{user_id}` | `member.remove` |
| PATCH | `/projects/{id}/members/{user_id}/role` | `role.assign` |
| GET | `/projects/{id}/roles` | `task.view` |
| POST | `/projects/{id}/roles` | `role.manage` |
| PATCH | `/projects/{id}/roles/{role_id}` | `role.manage` |
| DELETE | `/projects/{id}/roles/{role_id}` | `role.manage` |
| GET | `/permissions` | Autenticado. Catálogo completo para armar la interfaz de roles |

**POST `/projects/{id}/roles`**
```json
{
  "name": "Revisor",
  "color": "#B8860B",
  "permissions": ["task.view", "task.comment", "task.review"]
}
```
Respuesta `201` incluyendo `created_by` con el nombre de quien lo creó (RN-19).

Errores: `409 ROLE_NAME_TAKEN`, `422` si falta `task.view` (RN-05), `409 ROLE_HAS_MEMBERS` al borrar, `409 SYSTEM_ROLE_IMMUTABLE` al editar un rol predeterminado.

**DELETE `/projects/{id}/members/{user_id}`** devuelve `409 LAST_PROJECT_ADMIN` si dejaría el proyecto sin nadie con `project.archive` (RN-14).

---

## 5. Tareas — `/projects/{project_id}/tasks` y `/tasks`

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/projects/{pid}/tasks` | `task.view`. Filtros `?status=&assignee_id=&periodicity=&overdue=true` |
| POST | `/projects/{pid}/tasks` | `task.create` |
| GET | `/tasks/{id}` | `task.view` del proyecto |
| PATCH | `/tasks/{id}` | `task.edit_any` |
| DELETE | `/tasks/{id}` | `task.delete` |
| POST | `/tasks/{id}/assignees` | `task.assign` |
| DELETE | `/tasks/{id}/assignees/{user_id}` | `task.assign` |
| POST | `/tasks/{id}/status` | Ver máquina de estados |
| GET | `/me/tasks` | Autenticado. Tareas propias entre todos los proyectos |

**POST `/projects/{pid}/tasks`**
```json
{
  "title": "Entrenar el modelo base",
  "description": "...",
  "periodicity": "WEEKLY",
  "due_date": "2026-09-20",
  "assignee_ids": ["uuid-1", "uuid-2"]
}
```

Toda respuesta de tarea tiene esta forma:

```json
{
  "id": "...",
  "project_id": "...",
  "title": "Entrenar el modelo base",
  "description": "...",
  "status": "BACKLOG",
  "periodicity": "WEEKLY",
  "due_date": "2026-09-20",
  "is_overdue": false,
  "assignees": [{ "id": "...", "full_name": "Ana Gómez", "email": "..." }],
  "created_by": { "id": "...", "full_name": "Carlos", "email": "..." },
  "completed_at": null,
  "created_at": "...",
  "updated_at": "..."
}
```

`is_overdue` lo calcula el servidor comparando `due_date` con la fecha de hoy en `America/Bogota`, y **no** se guarda en ninguna columna (`data-model.md` §8). Viaja en la respuesta para que la insignia de la tarjeta y el filtro `?overdue=true` no puedan discrepar.

Un responsable debe ser miembro activo del proyecto; asignar a alguien de fuera devuelve `422`. Perder la membresía después no deshace la asignación: la tarea conserva su historial (RF-16, EB-04).

**POST `/tasks/{id}/assignees`** recibe `{ "user_id": "uuid" }`. Tanto este endpoint como `DELETE /tasks/{id}/assignees/{user_id}` responden `200` con la tarea completa, que es lo que el tablero tiene que volver a pintar.

**POST `/tasks/{id}/status`**
```json
{ "status": "IN_REVIEW" }
```
Errores: `409 INVALID_TRANSITION` con el detalle de las transiciones válidas desde el estado actual; `409 SUBMISSION_REQUIRED` al intentar pasar a `IN_REVIEW` sin entrega registrada.

Las dos transiciones que salen de `IN_REVIEW` no se hacen por aquí: aprobar marca la entrega y devolver exige un comentario (RN-07, RN-09), así que van por `POST /submissions/{id}/review`. Pedirlas a este endpoint devuelve `409 INVALID_TRANSITION`.

**GET `/me/tasks`** acepta `?due_before=&status=` y devuelve cada tarea con el nombre de su proyecto, para alimentar el panel de inicio.

---

## 6. Entregas y comentarios

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/tasks/{id}/submissions` | `task.view` |
| POST | `/tasks/{id}/submissions` | Ser responsable de la tarea |
| PATCH | `/submissions/{id}` | Autor, solo mientras esté `PENDING` |
| POST | `/submissions/{id}/review` | `task.review` y no ser responsable |
| GET | `/tasks/{id}/comments` | `task.view` |
| POST | `/tasks/{id}/comments` | `task.comment` |
| PATCH | `/comments/{id}` | Autor |
| DELETE | `/comments/{id}` | Autor, o `task.delete` para moderar |

**POST `/tasks/{id}/submissions`**
```json
{
  "description": "Entrené el modelo base con los datos de agosto. Exactitud del 0.87 en validación.",
  "commit_url": "https://github.com/semillero-ml/anomalias/commit/a1b2c3d"
}
```
Efecto secundario: mueve la tarea a `IN_REVIEW` en la misma transacción.
Errores: `409 SUBMISSION_ALREADY_PENDING`, `422` si `commit_url` no es un enlace de GitHub, `403 NOT_ASSIGNEE`.

**POST `/submissions/{id}/review`**
```json
{ "approved": false, "comment": "Falta la evaluación en el conjunto de prueba." }
```
Aprobar lleva la tarea a `DONE` y registra `completed_at`; devolver la lleva a `IN_PROGRESS`. Al aprobar, el comentario es opcional y se conserva si viene.
Notifica a quien registró la entrega (RF-42).
Errores: `422 REVIEW_COMMENT_REQUIRED` al devolver sin comentario, `403 CANNOT_REVIEW_OWN_SUBMISSION` (RN-07), `409 SUBMISSION_ALREADY_REVIEWED` si ya se resolvió.

`CANNOT_REVIEW_OWN_SUBMISSION` cubre las dos salidas de `IN_REVIEW`, no solo la aprobación: si un responsable pudiera devolverse su propia entrega, el segundo par de ojos que exige RN-07 sería opcional.

**PATCH `/submissions/{id}`**
```json
{ "description": "Agregué la evaluación en prueba.", "commit_url": null }
```
Solo el autor, y solo mientras la entrega siga `PENDING` (RN-12).
Errores: `403` si no es el autor, `409 SUBMISSION_ALREADY_REVIEWED` si ya la revisaron.

---

## 7. Notificaciones — `/notifications`

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/notifications` | Autenticado. `?unread_only=true` |
| GET | `/notifications/unread-count` | Autenticado |
| POST | `/notifications/{id}/read` | Autenticado, propias |
| POST | `/notifications/read-all` | Autenticado |
| GET | `/admin/notification-settings` | Rol global `ADMIN` |
| PUT | `/admin/notification-settings` | Rol global `ADMIN` |

**PUT `/admin/notification-settings`**
```json
{
  "reminder_days_before": [5, 2, 0],
  "send_hour": 7,
  "overdue_enabled": true
}
```
Validaciones: máximo 5 valores en `reminder_days_before`, cada uno entre 0 y 30, sin repetidos; `send_hour` entre 0 y 23.

**GET `/notifications`** devuelve una página: `{ items, total, page, size }`, con `page` y `size` como parámetros y las más nuevas primero.
**GET `/notifications/unread-count`** responde `{ "unread": 3 }`.
**POST `/notifications/read-all`** responde `{ "marked": 2 }`, el número de filas que estaban sin leer.

Una notificación ajena responde **404**, no 403: un 403 confirmaría que existe.

**Consulta del contador de no leídas:** el frontend la ejecuta cada 60 segundos mientras la pestaña esté visible. No se usan WebSockets ni eventos del servidor: mantener una conexión abierta contra un servicio que se suspende no tiene sentido.

---

## 8. Lecciones — `/lessons`

| Método | Ruta | Requisito |
|---|---|---|
| GET | `/lesson-modules` | Autenticado. Solo publicados, salvo para `ADMIN` y `LESSON_EDITOR` |
| POST | `/lesson-modules` | `ADMIN` o `LESSON_EDITOR` |
| PATCH | `/lesson-modules/{id}` | `ADMIN` o `LESSON_EDITOR` |
| DELETE | `/lesson-modules/{id}` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lesson-modules/{id}/publish` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lesson-modules/reorder` | `ADMIN` o `LESSON_EDITOR` |
| GET | `/lessons/{id}` | Autenticado, si está publicada |
| POST | `/lesson-modules/{id}/lessons` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lesson-modules/{id}/lessons/reorder` | `ADMIN` o `LESSON_EDITOR` |
| PATCH | `/lessons/{id}` | `ADMIN` o `LESSON_EDITOR` |
| DELETE | `/lessons/{id}` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lessons/{id}/publish` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lessons/{id}/resources` | `ADMIN` o `LESSON_EDITOR` |
| POST | `/lessons/{id}/resources/reorder` | `ADMIN` o `LESSON_EDITOR` |
| DELETE | `/resources/{id}` | `ADMIN` o `LESSON_EDITOR` |

Las tres rutas de publicación y reordenamiento de lecciones y recursos se agregaron en la Fase 6: el RF-47 nombra despublicar **lecciones**, no solo módulos, y el RF-50 pide orden manual en los **tres** niveles. Tienen la misma forma que sus equivalentes de módulo, para que no haya dos convenciones.

**GET `/lesson-modules`** devuelve el árbol completo (módulos con sus lecciones y el conteo de recursos) en una sola petición. Con la escala prevista, decenas de módulos como mucho, paginar sería complicar sin motivo. Acepta `?q=` para buscar en el título y la descripción, de módulos y de lecciones (RF-51); la visibilidad se aplica antes que el texto, así que una búsqueda nunca delata la existencia de un borrador.

**POST `/lesson-modules/{id}/publish`** recibe `{ "published": true | false }`. Un solo endpoint para las dos direcciones que nombra el RF-47: publicar y despublicar son la misma decisión con el valor contrario, y separarlas serían dos sitios donde olvidar una regla. El `PATCH` correspondiente **no** admite `is_published`, para que haya un único camino por operación.

**POST `/lesson-modules/reorder`** recibe `{ "ids": [...] }` con el orden completo, no un movimiento suelto. El servidor exige que la lista nombre exactamente los módulos que existen y responde `422` si no coincide: una lista parcial obligaría a adivinar dónde va el resto, y la adivinanza fallaría justo cuando importa, cuando otro editor agregó algo mientras se arrastraba el orden.

**GET `/lessons/{id}`** devuelve `404`, no `403`, cuando la lección está en borrador o su módulo lo está (RN-33). Aquí el 404 no oculta pertenencia como en los proyectos: impide recorrer identificadores para averiguar qué se está preparando.

**DELETE `/lessons/{id}`** no exige confirmación: el RN-36 la pide cuando desaparecería un módulo entero, y una lección contiene enlaces, no lecciones.

**DELETE `/lesson-modules/{id}`** exige `?confirm=true` y devuelve `409` con el código `CONFIRMATION_REQUIRED` sin ese parámetro, con el conteo exacto en `details`: `{ "lessons": 3 }` (RN-36).

---

## 9. Endpoints internos y de sistema

| Método | Ruta | Autenticación |
|---|---|---|
| GET | `/health` | Pública. Ejecuta `SELECT 1`; sirve de sonda y despierta de paso la API y la base antes del proceso diario |
| POST | `/internal/jobs/reminders` | `X-Job-Token` |

**POST `/internal/jobs/reminders`** responde con el resumen de la ejecución:
```json
{
  "executed_at": "2026-09-05T12:00:03Z",
  "due_soon_sent": 7,
  "overdue_sent": 2,
  "skipped_duplicates": 3,
  "failures": 0
}
```
No aparece en el esquema público de OpenAPI.

---

## 10. Códigos de error

| Código | HTTP | Cuándo |
|---|---|---|
| `UNAUTHENTICATED` | 401 | Token ausente, vencido o inválido |
| `FORBIDDEN` | 403 | Autenticado sin el permiso necesario |
| `NOT_FOUND` | 404 | Recurso inexistente o sin visibilidad para el usuario |
| `VALIDATION_ERROR` | 422 | Cuerpo inválido |
| `INVALID_TRANSITION` | 409 | Cambio de estado no permitido |
| `SUBMISSION_REQUIRED` | 409 | Falta la entrega para pasar a revisión |
| `SUBMISSION_ALREADY_PENDING` | 409 | Ya hay una entrega sin revisar |
| `SUBMISSION_ALREADY_REVIEWED` | 409 | La entrega ya fue aprobada o devuelta |
| `NOT_ASSIGNEE` | 403 | Quien entrega no es responsable de la tarea |
| `REVIEW_COMMENT_REQUIRED` | 422 | Devolución sin comentario |
| `CANNOT_REVIEW_OWN_SUBMISSION` | 403 | El revisor es responsable de la tarea |
| `PROJECT_ARCHIVED` | 409 | Escritura sobre proyecto archivado |
| `ROLE_NAME_TAKEN` | 409 | Nombre de rol repetido en el proyecto |
| `ROLE_HAS_MEMBERS` | 409 | Borrado de rol con miembros |
| `SYSTEM_ROLE_IMMUTABLE` | 409 | Edición de un rol predeterminado |
| `LAST_ADMIN` | 409 | Quedaría el sistema sin administradores |
| `LAST_PROJECT_ADMIN` | 409 | Quedaría el proyecto sin administrador |
| `EMAIL_ALREADY_REGISTERED` | 409 | Invitación a un correo con cuenta |
| `INVITATION_EXPIRED` | 409 | Token de invitación vencido |
| `INVITATION_ALREADY_USED` | 409 | Token ya utilizado |
| `CONFIRMATION_REQUIRED` | 409 | Borrado en cascada sin `?confirm=true`; `details` trae el conteo |
