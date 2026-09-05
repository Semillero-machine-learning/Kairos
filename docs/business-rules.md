# Reglas de negocio

Este documento es la fuente de verdad para las decisiones de autorización y para las transiciones de estado. Ante cualquier contradicción con otro documento, manda este.

---

## 1. Los dos planos de roles

El sistema tiene **dos sistemas de roles independientes** que no se mezclan nunca.

### Plano global (fijo)

Definido por el sistema, no editable por nadie. Un usuario tiene **exactamente uno**.

| Rol global | Facultades |
|---|---|
| `ADMIN` | Invitar y desactivar usuarios, cambiar roles globales, crear y archivar proyectos, designar líderes, configurar notificaciones, publicar lecciones. Además, acceso de lectura a todos los proyectos. |
| `LESSON_EDITOR` | Gestionar el catálogo de lecciones. Nada más a nivel global. |
| `MEMBER` | Ninguna facultad global. Todo lo que puede hacer depende de sus roles en cada proyecto. |

**RN-01.** El rol global `ADMIN` **no** otorga permisos de escritura dentro de un proyecto. Un administrador que quiera crear tareas en un proyecto debe ser miembro de ese proyecto con un rol que se lo permita. Sí tiene lectura universal, para poder supervisar.

**RN-02.** Siempre debe existir al menos un usuario con rol global `ADMIN` y estado activo. Toda operación que dejaría el sistema sin administradores activos se rechaza.

### Plano de proyecto (dinámico)

Cada proyecto tiene su propio conjunto de roles. Un usuario tiene **exactamente un rol por proyecto** del que es miembro.

**RN-03.** Un rol de proyecto pertenece a un único proyecto. No hay roles compartidos ni plantillas globales.

**RN-04.** Ser Líder del proyecto A no otorga absolutamente nada en el proyecto B.

---

## 2. Roles predeterminados de proyecto

Se crean automáticamente al crear el proyecto. Son roles del sistema (`is_system = true`): no se pueden eliminar ni renombrar, y su conjunto de permisos no se puede alterar.

| Rol | Color | Permisos |
|---|---|---|
| **Líder** | `#1F6F5C` | Todos los del catálogo |
| **Colaborador** | `#2E5C8A` | `task.view`, `task.comment` |
| **Observador** | `#6B6B6B` | `task.view`, `task.comment` |

La diferencia entre Colaborador y Observador **no** está en el catálogo de permisos, sino en las reglas implícitas de propiedad (sección 5): un Colaborador es alguien a quien se le asignan tareas y por eso puede mover y entregar las suyas; un Observador normalmente no tiene tareas asignadas. Si a un Observador se le asigna una tarea, adquiere sobre ella las mismas facultades implícitas. Se distinguen para que el tablero y los filtros comuniquen la intención del líder.

---

## 3. Catálogo de permisos de proyecto

Es una lista **cerrada**. Los roles personalizados se arman escogiendo de aquí; no se pueden inventar permisos nuevos sin cambiar el código.

| Código | Qué habilita |
|---|---|
| `task.view` | Ver el proyecto, su tablero y sus tareas. Sin este permiso el usuario no ve nada del proyecto. |
| `task.comment` | Comentar en las tareas. |
| `task.create` | Crear tareas. |
| `task.edit_any` | Editar título, descripción, periodicidad y fecha límite de cualquier tarea. |
| `task.delete` | Eliminar tareas (borrado lógico). |
| `task.assign` | Agregar o quitar responsables de una tarea. |
| `task.change_status_any` | Mover cualquier tarea entre estados, incluidas las ajenas. |
| `task.review` | Aprobar o devolver entregas. |
| `member.add` | Agregar al proyecto usuarios que ya existen en la plataforma. |
| `member.remove` | Retirar miembros del proyecto. |
| `role.assign` | Cambiar el rol de proyecto de un miembro. |
| `role.manage` | Crear, editar y eliminar roles personalizados del proyecto. |
| `project.edit` | Editar nombre, descripción y fechas del proyecto. |
| `project.archive` | Archivar y desarchivar el proyecto. |

**RN-05.** `task.view` es obligatorio en todo rol. Un rol sin `task.view` no tiene sentido y se rechaza al crearlo.

**RN-06.** Los permisos no se implican entre sí en el código. Si un rol tiene `task.review` pero no `task.view`, es un rol inválido (ver RN-05); fuera de esa regla, cada permiso se verifica de forma independiente.

---

## 4. Ciclo de vida de la tarea

### Estados

`BACKLOG` → `TODO` → `IN_PROGRESS` → `IN_REVIEW` → `DONE`

### Transiciones permitidas

| Desde | Hacia | Quién | Condición |
|---|---|---|---|
| `BACKLOG` | `TODO` | `task.change_status_any` | — |
| `TODO` | `IN_PROGRESS` | Responsable de la tarea, o `task.change_status_any` | — |
| `TODO` | `BACKLOG` | `task.change_status_any` | — |
| `IN_PROGRESS` | `TODO` | Responsable, o `task.change_status_any` | — |
| `IN_PROGRESS` | `IN_REVIEW` | Responsable, o `task.change_status_any` | **Exige registrar una entrega** con descripción no vacía |
| `IN_REVIEW` | `DONE` | `task.review` | Marca la entrega como aprobada |
| `IN_REVIEW` | `IN_PROGRESS` | `task.review` | Devolución: **exige comentario de revisión no vacío** |
| `DONE` | `IN_PROGRESS` | `task.change_status_any` | Reapertura. Registra una nueva ronda de trabajo |

**Cualquier transición que no aparezca en esta tabla se rechaza con error 409.** En particular: no se salta de `TODO` a `DONE`, ni de `IN_REVIEW` a `TODO`, ni de `BACKLOG` a `IN_PROGRESS`.

**RN-07.** Solo un usuario con `task.review` puede sacar una tarea de `IN_REVIEW`. Quien entregó no puede aprobarse a sí mismo, ni siquiera si tiene `task.review`: si el revisor es también responsable de la tarea, la aprobación se rechaza. Esto obliga a que exista un segundo par de ojos.

**RN-08.** Al aprobar, la tarea registra `completed_at` con la fecha y hora del momento. Al reabrirse, `completed_at` vuelve a nulo.

**RN-09.** Todas las entregas se conservan. Una devolución no borra la entrega anterior: queda con estado `REJECTED` y la nueva entrega se apila encima.

---

## 5. Reglas implícitas de propiedad

Independientes del catálogo de permisos. Aplican a todo miembro del proyecto con `task.view`:

**RN-10.** Un responsable puede mover **sus propias** tareas entre `TODO` e `IN_PROGRESS`, y llevarlas a `IN_REVIEW` registrando la entrega, sin necesitar `task.change_status_any`.

**RN-11.** El autor de un comentario puede editarlo o borrarlo. Nadie más puede editar comentarios ajenos; el líder con `task.delete` puede borrar comentarios ajenos por moderación.

**RN-12.** Un usuario puede editar su propia entrega mientras la tarea siga en `IN_REVIEW` y nadie la haya revisado.

---

## 6. Reglas de proyecto

**RN-13.** Solo `ADMIN` crea proyectos. Al crearlos designa un líder inicial, que queda como miembro con el rol Líder.

**RN-14.** Un proyecto no puede quedarse sin ningún miembro con el permiso `project.archive`. La operación que dejaría al proyecto sin nadie capaz de administrarlo (retirar al último líder, o cambiarle el rol) se rechaza. El `ADMIN` siempre puede reasignar el liderazgo.

**RN-15.** Un proyecto **archivado** es de solo lectura absoluta: no admite crear ni editar tareas, comentar, entregar, revisar, agregar miembros ni modificar roles. Solo se permite desarchivarlo.

**RN-16.** Archivar un proyecto detiene toda notificación relacionada, incluidos los recordatorios de tareas vencidas.

**RN-17.** Los proyectos y sus tareas nunca se eliminan físicamente.

---

## 7. Reglas de roles personalizados

**RN-18.** Crear, editar o eliminar roles personalizados requiere `role.manage`, que por defecto solo tiene el Líder.

**RN-19.** El sistema guarda `created_by` y `created_at` de cada rol personalizado, y la interfaz muestra quién lo creó.

**RN-20.** El nombre de un rol es único dentro del proyecto, sin distinguir mayúsculas.

**RN-21.** Un rol con miembros asignados no puede eliminarse. Hay que reasignar primero a esos miembros.

**RN-22.** Editar los permisos de un rol surte efecto inmediato para todos sus miembros, sin necesidad de que vuelvan a iniciar sesión. Por eso los permisos **no se guardan dentro del JWT**: se consultan en cada petición.

**RN-23.** Los roles del sistema (`is_system = true`) no admiten edición ni eliminación.

---

## 8. Reglas de notificación

**RN-24.** Toda notificación se entrega por dos canales: registro dentro de la aplicación y correo electrónico. El registro en la aplicación se crea siempre; el correo puede fallar sin afectar nada más.

**RN-25.** Eventos que generan notificación:

| Evento | Destinatarios |
|---|---|
| Usuario agregado como responsable de una tarea | El responsable agregado |
| Recordatorio previo al vencimiento | Todos los responsables de la tarea |
| Tarea vencida | Todos los responsables **más** los miembros con `task.review` del proyecto |
| Entrega aprobada o devuelta | Quien registró la entrega |
| Invitación a la plataforma | El invitado |
| Restablecimiento de contraseña | El solicitante |

**RN-26.** La configuración de recordatorios es única para toda la plataforma y solo la modifica un `ADMIN`:

- `reminder_days_before`: lista de enteros, por defecto `[3, 1, 0]`
- `send_hour`: entero de 0 a 23, por defecto `7`
- `timezone`: fijo en `America/Bogota`
- `overdue_enabled`: booleano, por defecto verdadero

**RN-27 (idempotencia).** Un mismo usuario no recibe dos veces el mismo tipo de recordatorio para la misma tarea el mismo día. Se garantiza con una restricción de unicidad sobre `(user_id, task_id, kind, target_date)` en la tabla de despachos.

**RN-28.** No se notifica sobre tareas en estado `DONE`, ni de proyectos archivados, ni a usuarios desactivados.

**RN-29.** Si el proceso programado se salta un día, al reanudarse solo envía lo que corresponde al día en curso. No reconstruye avisos atrasados.

**RN-30.** Un fallo de envío de correo se registra y se reintenta hasta 3 veces con espera creciente. Nunca revierte ni bloquea la operación de negocio que lo originó.

---

## 9. Reglas de lecciones

**RN-31.** Solo `ADMIN` y `LESSON_EDITOR` pueden crear, editar, publicar o despublicar módulos y lecciones. Los líderes de proyecto no.

**RN-32.** Los módulos y lecciones en borrador solo son visibles para `ADMIN` y `LESSON_EDITOR`.

**RN-33.** Una lección publicada dentro de un módulo en borrador **no es visible**: el módulo manda.

**RN-34.** La plataforma no aloja archivos. Todo recurso es una URL externa.

**RN-35.** No se registra progreso, avance ni finalización por usuario.

**RN-36.** Al eliminar un módulo se eliminan sus lecciones y recursos en cascada. La interfaz debe advertirlo con el conteo exacto de lecciones que se perderán.

---

## 10. Reglas de autenticación

**RN-37.** No existe el registro abierto. La única vía de entrada es una invitación creada por un `ADMIN`.

**RN-38.** El token de invitación tiene vigencia de 7 días, es de un solo uso, y se almacena hasheado. Reenviar una invitación invalida el token anterior.

**RN-39.** Aceptar una invitación exige nombre completo y contraseña de mínimo 10 caracteres. La cuenta se crea en ese momento; antes de aceptar, el usuario no existe como tal.

**RN-40.** No hay verificación de correo aparte. Recibir y usar el enlace de invitación ya prueba control de la dirección.

**RN-41.** El token de restablecimiento de contraseña vive 1 hora, es de un solo uso y se guarda hasheado. Solicitar el restablecimiento devuelve siempre la misma respuesta, exista o no la cuenta.

**RN-42.** Restablecer o cambiar la contraseña revoca todos los tokens de refresco vigentes del usuario.

**RN-43.** El token de refresco es rotativo: cada uso emite uno nuevo y revoca el anterior. Si se detecta el uso de un token ya revocado, se revocan todas las sesiones de ese usuario.

**RN-44.** Un usuario desactivado no puede iniciar sesión y sus tokens de refresco se revocan en el acto.

---

## 11. Matriz de autorización resumida

| Operación | Requisito |
|---|---|
| Invitar usuario a la plataforma | Rol global `ADMIN` |
| Desactivar usuario / cambiar rol global | Rol global `ADMIN` |
| Crear proyecto | Rol global `ADMIN` |
| Ver un proyecto | Miembro con `task.view`, o rol global `ADMIN` (solo lectura) |
| Editar proyecto | `project.edit` |
| Archivar / desarchivar | `project.archive` |
| Agregar miembro al proyecto | `member.add` |
| Retirar miembro | `member.remove` |
| Cambiar rol de un miembro | `role.assign` |
| Crear / editar / borrar rol personalizado | `role.manage` |
| Crear tarea | `task.create` |
| Editar cualquier tarea | `task.edit_any` |
| Eliminar tarea | `task.delete` |
| Asignar responsables | `task.assign` |
| Mover tarea propia (TODO ↔ IN_PROGRESS → IN_REVIEW) | Ser responsable |
| Mover cualquier tarea | `task.change_status_any` |
| Aprobar o devolver entrega | `task.review` y **no** ser responsable de esa tarea |
| Comentar | `task.comment` |
| Configurar recordatorios | Rol global `ADMIN` |
| Crear / editar / publicar lecciones | Rol global `ADMIN` o `LESSON_EDITOR` |
| Ver lecciones publicadas | Cualquier usuario autenticado |
