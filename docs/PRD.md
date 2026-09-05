# PRD — Plataforma de Gestión del Semillero de Machine Learning

**Versión:** 1.0
**Estado:** Aprobado para implementación
**Última actualización:** 2026-09-05

---

## 1. Contexto y objetivo

El semillero de Machine Learning coordina hoy sus proyectos, tareas y material de estudio por canales informales (chats, carpetas sueltas, repositorios dispersos). Esto genera tres problemas: nadie sabe con certeza qué tareas tiene asignadas, los vencimientos se pasan sin aviso, y el material de estudio está regado.

La plataforma resuelve esos tres problemas con un producto interno tipo Jira reducido: proyectos con tablero Kanban, tareas con responsables y fecha límite, recordatorios automáticos por correo, y un catálogo de lecciones que apunta al material ya existente en GitHub.

**No es un objetivo** replicar Jira. Todo lo que no sirva directamente a esos tres problemas queda fuera del alcance (ver sección 9).

### 1.1 Métricas de éxito

| Métrica | Objetivo |
|---|---|
| Adopción | 100% de los miembros activos con cuenta creada en las primeras 2 semanas |
| Tareas vencidas sin entrega | Reducción respecto al semestre anterior |
| Costo de operación | 0 USD/mes en infraestructura (solo el dominio, ~10 USD/año) |
| Tiempo de carga inicial | Ver RNF-02 |

---

## 2. Usuarios y actores

| Actor | Descripción |
|---|---|
| **Administrador** | Coordinador del semillero. Invita usuarios, crea proyectos, asigna roles globales, configura las notificaciones y publica lecciones. |
| **Editor de Lecciones** | Rol global. Publica y mantiene el catálogo de lecciones. No tiene privilegios sobre proyectos. |
| **Miembro** | Rol global base. Participa en los proyectos a los que se le agregue, con los permisos que le dé su rol *dentro de cada proyecto*. |
| **Líder de proyecto** | No es un rol global. Es un rol **dentro de un proyecto**: quien lo tiene gestiona ese proyecto y solo ese. |
| **Sistema (scheduler)** | Proceso programado externo que dispara el envío de recordatorios. |

> **Concepto clave — dos planos de roles.** Existen roles **globales** (fijos, definidos por el sistema: Administrador, Editor de Lecciones, Miembro) y roles **de proyecto** (dinámicos, con permisos configurables, propios de cada proyecto). Un usuario tiene exactamente un rol global y, además, un rol distinto en cada proyecto del que forme parte. Ser líder del proyecto A no otorga absolutamente nada en el proyecto B.

---

## 3. Requisitos funcionales

### 3.1 Autenticación y acceso (RF-01 a RF-09)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-01 | El registro es **cerrado**. Nadie puede crear una cuenta por su cuenta; el acceso se otorga solo por invitación de un Administrador. | Debe |
| RF-02 | El Administrador genera una invitación indicando correo y rol global. El sistema crea un enlace con token de un solo uso, con vigencia de 7 días, y lo envía por correo. El enlace también puede copiarse para compartirlo por otro canal. | Debe |
| RF-03 | El invitado abre el enlace, define su nombre y contraseña, y con eso queda creada su cuenta. El token se invalida en el momento de usarse. | Debe |
| RF-04 | El Administrador puede reenviar una invitación (lo cual invalida el token anterior y genera uno nuevo) y revocar una invitación pendiente. | Debe |
| RF-05 | Inicio de sesión con correo y contraseña. Devuelve un token de acceso y un token de refresco. | Debe |
| RF-06 | Cierre de sesión: revoca el token de refresco vigente. | Debe |
| RF-07 | Recuperación de contraseña: el usuario solicita el restablecimiento con su correo, recibe un enlace con token de un solo uso y vigencia de 1 hora, y define una nueva contraseña. La respuesta del endpoint de solicitud es idéntica exista o no el correo, para no filtrar qué direcciones están registradas. | Debe |
| RF-08 | Un usuario autenticado puede cambiar su contraseña indicando la actual, y puede editar su nombre. | Debe |
| RF-09 | El Administrador puede **desactivar** un usuario. Un usuario desactivado no puede iniciar sesión, deja de recibir notificaciones y no aparece en los selectores de asignación, pero su historial (tareas, entregas, comentarios) permanece intacto y visible. No existe la eliminación física de usuarios. | Debe |

### 3.2 Usuarios y roles globales (RF-10 a RF-12)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-10 | El Administrador ve el listado de usuarios con nombre, correo, rol global, estado y fecha de ingreso, con búsqueda por nombre o correo. | Debe |
| RF-11 | El Administrador puede cambiar el rol global de cualquier usuario. | Debe |
| RF-12 | El sistema garantiza que siempre exista al menos un Administrador activo: no se permite que el último Administrador se degrade a sí mismo ni se desactive. | Debe |

### 3.3 Proyectos (RF-13 a RF-19)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-13 | Solo el Administrador crea proyectos, indicando nombre, descripción y fecha de inicio. | Debe |
| RF-14 | Al crear un proyecto, el Administrador designa a su primer líder. El sistema crea automáticamente los tres roles de proyecto predeterminados (Líder, Colaborador, Observador) y agrega al designado con el rol Líder. | Debe |
| RF-15 | Quien tenga el permiso `member.add` puede agregar al proyecto usuarios **ya existentes** en la plataforma, asignándoles un rol del proyecto. Desde un proyecto no se invita gente nueva a la plataforma. | Debe |
| RF-16 | Quien tenga `member.remove` puede retirar miembros del proyecto. Retirar a un miembro **no** borra sus tareas ni entregas: la tarea queda sin ese responsable y el historial se conserva. | Debe |
| RF-17 | Quien tenga `role.assign` puede cambiar el rol que un miembro tiene dentro del proyecto. | Debe |
| RF-18 | Un proyecto puede archivarse (`project.archive`). Un proyecto archivado es de **solo lectura**: se consulta completo, con todas sus tareas y entregas, pero no admite ninguna modificación ni genera notificaciones. Puede desarchivarse. | Debe |
| RF-19 | Los proyectos nunca se eliminan. | Debe |

### 3.4 Roles y permisos de proyecto (RF-20 a RF-24)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-20 | Cada proyecto nace con tres roles del sistema: **Líder** (todos los permisos), **Colaborador** (ver, comentar, mover y entregar sus propias tareas) y **Observador** (ver y comentar). Estos roles no se pueden eliminar ni renombrar. | Debe |
| RF-21 | Quien tenga `role.manage` puede crear roles personalizados **dentro de su proyecto**, con nombre, color y una selección libre de permisos del catálogo (ver `business-rules.md`, sección 3). | Debe |
| RF-22 | El sistema registra qué usuario creó cada rol personalizado y cuándo, y esa información se muestra en la interfaz de administración de roles del proyecto. | Debe |
| RF-23 | Un rol personalizado solo existe dentro del proyecto donde fue creado. No se comparte entre proyectos. | Debe |
| RF-24 | Un rol personalizado no puede eliminarse mientras tenga miembros asignados; primero hay que reasignarlos. | Debe |

### 3.5 Tareas (RF-25 a RF-37)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-25 | Quien tenga `task.create` crea tareas dentro de un proyecto con: título, descripción, periodicidad, fecha límite y responsables. | Debe |
| RF-26 | La **periodicidad** (Puntual, Semanal, Mensual, Semestral) es una etiqueta descriptiva. **No genera tareas automáticamente.** Sirve para filtrar y para que el equipo entienda el ritmo esperado. | Debe |
| RF-27 | Una tarea puede tener uno o varios responsables. | Debe |
| RF-28 | La tarea recorre cinco estados fijos: `BACKLOG` → `TODO` → `IN_PROGRESS` → `IN_REVIEW` → `DONE`. Las transiciones permitidas están en `business-rules.md`, sección 4. | Debe |
| RF-29 | El proyecto se visualiza como tablero Kanban con una columna por estado, con arrastrar y soltar en escritorio y un selector de estado en móvil. | Debe |
| RF-30 | Un responsable mueve sus propias tareas entre `TODO` e `IN_PROGRESS` sin permisos adicionales. Mover tareas ajenas requiere `task.change_status_any`. | Debe |
| RF-31 | Para pasar una tarea a `IN_REVIEW`, el responsable debe registrar una **entrega**: descripción obligatoria de lo que hizo y, opcionalmente, la URL del commit o pull request en GitHub. | Debe |
| RF-32 | La URL de la entrega se valida contra el formato de enlaces de GitHub (commit, pull request o árbol de repositorio). No se suben archivos a la plataforma. | Debe |
| RF-33 | Quien tenga `task.review` aprueba la entrega (la tarea pasa a `DONE`) o la devuelve con un comentario obligatorio (la tarea vuelve a `IN_PROGRESS`). | Debe |
| RF-34 | Una tarea guarda todo su historial de entregas, no solo la última. | Debe |
| RF-35 | Las tareas admiten comentarios de cualquier miembro con `task.comment`. El autor puede editar o borrar los suyos. | Debe |
| RF-36 | El tablero se filtra por responsable, periodicidad, estado y "vencidas". Existe además una vista personal "Mis tareas" que cruza todos los proyectos del usuario. | Debe |
| RF-37 | Las tareas se pueden eliminar solo con `task.delete`, y el borrado es lógico. | Debería |

### 3.6 Notificaciones (RF-38 a RF-45)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-38 | Toda notificación se entrega por dos canales: dentro de la aplicación (campana con historial y contador de no leídas) y por correo electrónico. | Debe |
| RF-39 | **Asignación de tarea:** cuando un usuario es agregado como responsable, recibe una notificación inmediata con el título de la tarea, el proyecto y la fecha límite. | Debe |
| RF-40 | **Recordatorio de vencimiento:** los responsables de una tarea sin terminar reciben un aviso los días previos configurados por el Administrador. | Debe |
| RF-41 | **Tarea vencida:** pasada la fecha límite sin que la tarea esté en `DONE`, se notifica a los responsables y, adicionalmente, al líder del proyecto. | Debe |
| RF-42 | **Entrega revisada:** cuando una entrega es aprobada o devuelta, se notifica a quien la envió. | Debe |
| RF-43 | La configuración de recordatorios es **global**, no por proyecto, y solo el Administrador la modifica: días de aviso previo (por defecto 3, 1 y 0), hora de envío (por defecto 07:00 hora de Colombia) e interruptor de avisos de tareas vencidas. | Debe |
| RF-44 | El sistema nunca envía el mismo recordatorio dos veces al mismo usuario para la misma tarea en el mismo día, aunque el proceso programado se ejecute varias veces. | Debe |
| RF-45 | Los proyectos archivados y los usuarios desactivados no generan ni reciben notificaciones. | Debe |

### 3.7 Lecciones (RF-46 a RF-52)

| ID | Requisito | Prioridad |
|---|---|---|
| RF-46 | El catálogo de lecciones se organiza en **módulos**; cada módulo agrupa **lecciones** ordenadas; cada lección contiene una lista de **recursos**. | Debe |
| RF-47 | Solo el Administrador y el Editor de Lecciones pueden crear, editar, publicar o despublicar módulos y lecciones. Los líderes de proyecto **no** tienen esta facultad. | Debe |
| RF-48 | Un recurso tiene tipo (Notebook, PDF, Video, Repositorio, Artículo), título y URL. La plataforma **no aloja archivos**: solo enlaza al material de GitHub y otras fuentes. | Debe |
| RF-49 | Los módulos y lecciones tienen estado borrador o publicado. Los borradores solo son visibles para el Administrador y el Editor de Lecciones. | Debe |
| RF-50 | El orden de módulos, lecciones y recursos es definido manualmente por el editor. | Debe |
| RF-51 | Todos los usuarios autenticados pueden consultar el catálogo publicado y buscar por título o descripción. | Debe |
| RF-52 | No se registra progreso ni avance por usuario en las lecciones. | Debe |

---

## 4. Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | **Diseño adaptable.** La interfaz funciona en móvil (360 px de ancho en adelante), tablet y escritorio. El tablero Kanban cambia a vista de lista con selector de estado por debajo de 768 px. Las áreas táctiles miden al menos 44×44 px. |
| RNF-02 | **Arranque en frío.** El backend en el plan gratuito de Render se suspende tras ~15 minutos de inactividad y la primera petición puede tardar cerca de un minuto. El frontend debe mostrar un estado de carga explícito ("Despertando el servidor...") tras 3 segundos de espera, con reintento automático y tiempo de espera de 90 segundos. Un ping programado cada 10 minutos en horario hábil reduce la frecuencia del problema. |
| RNF-03 | **Costo cero.** Todo el sistema opera dentro de los planes gratuitos de Supabase, Render, Cloudflare/Vercel, GitHub Actions y Resend. El único gasto autorizado es el dominio. |
| RNF-04 | **Escala objetivo.** Diseñado para 50 usuarios, 10 proyectos activos y unas 1.000 tareas por semestre. No se requieren optimizaciones más allá de índices correctos. |
| RNF-05 | **Seguridad.** Contraseñas con Argon2id. Tokens de acceso JWT de 15 minutos; tokens de refresco de 7 días, rotativos y almacenados en la base de datos solo como hash. Los tokens de invitación y de restablecimiento se guardan hasheados. Toda comprobación de permisos ocurre en el backend; el frontend solo oculta lo que el usuario no puede hacer, nunca es la barrera. |
| RNF-06 | **Base de datos.** Modelo en tercera forma normal. Claves primarias UUID. Marcas de tiempo en `timestamptz` (UTC), presentadas al usuario en `America/Bogota`. |
| RNF-07 | **Suspensión de Supabase.** El plan gratuito pausa proyectos tras una semana sin actividad. El ping programado del RNF-02 golpea también la base de datos para evitarlo. |
| RNF-08 | **Disponibilidad.** No hay compromiso de disponibilidad. Es una herramienta interna; una caída temporal es aceptable. |
| RNF-09 | **Accesibilidad.** Contraste mínimo AA, navegación por teclado en formularios y tablero, etiquetas ARIA en los controles del Kanban. |
| RNF-10 | **Idioma.** Interfaz y documentación en español. Código, nombres de tablas, campos y endpoints en inglés. |
| RNF-11 | **Trazabilidad mínima.** Cada entidad guarda `created_at`, `updated_at` y el usuario creador. No se implementa una bitácora de auditoría completa. |

---

## 5. Escenarios de uso principales

**E-01 — Alta de un nuevo integrante.** El coordinador invita a `ana@ejemplo.com` como Miembro. Ana recibe el correo, abre el enlace, pone su contraseña y entra. Ve el catálogo de lecciones, pero ningún proyecto: todavía no la han agregado a ninguno.

**E-02 — Arranque de proyecto.** El coordinador crea "Detección de anomalías en series de tiempo" y designa a Carlos como líder. Carlos agrega a cuatro compañeros como Colaboradores, crea seis tareas y reparte responsables. Cada uno recibe correo y notificación en la aplicación.

**E-03 — Ciclo de una tarea.** Ana arrastra su tarea a "En progreso". Al terminar, la pasa a "En revisión" describiendo el trabajo y pegando el enlace del commit. Carlos revisa, encuentra que falta la evaluación del modelo y la devuelve con un comentario. La tarea vuelve a "En progreso" y Ana recibe el aviso. Al segundo intento, Carlos aprueba y la tarea queda en "Hecha".

**E-04 — Recordatorio automático.** A las 07:00, el proceso programado revisa las tareas sin terminar. Encuentra dos que vencen en 3 días y una vencida ayer. Envía correo y notificación a los responsables, y al líder únicamente por la vencida. Si el proceso se repite por un reintento, no se envía nada duplicado.

**E-05 — Rol a la medida.** Carlos necesita que un estudiante de otro semestre revise entregas sin poder crear ni borrar tareas. Crea el rol "Revisor" con `task.view`, `task.comment` y `task.review`, en color ámbar, y se lo asigna. El rol solo existe en ese proyecto y queda registrado que Carlos lo creó.

**E-06 — Cierre de semestre.** El coordinador archiva tres proyectos terminados. Dejan de aparecer en la lista activa y de generar recordatorios, pero cualquiera puede abrirlos y ver qué se hizo, quién lo hizo y con qué commits.

**E-07 — Publicación de material.** El Editor de Lecciones crea el módulo "Redes neuronales", agrega tres lecciones y enlaza los notebooks del repositorio público del semillero. Mientras están en borrador nadie más los ve; al publicar, aparecen para todos.

---

## 6. Escenarios de error y borde

| ID | Situación | Comportamiento esperado |
|---|---|---|
| EB-01 | Token de invitación vencido o ya usado | Mensaje claro y sugerencia de pedirle al administrador un nuevo enlace. Nunca se revela si el correo ya tiene cuenta. |
| EB-02 | Invitar un correo que ya tiene cuenta | Error 409 con mensaje explícito. |
| EB-03 | Invitación pendiente duplicada para el mismo correo | Se reemplaza la anterior: el token viejo queda invalidado. |
| EB-04 | Usuario retirado de un proyecto con tareas en curso | Las tareas se conservan y quedan sin ese responsable. Si quedan sin ningún responsable, se marcan visualmente como "sin asignar" en el tablero. |
| EB-05 | Intento de eliminar un rol con miembros asignados | Error 409 indicando cuántos miembros lo tienen. |
| EB-06 | Intento de modificar cualquier cosa en un proyecto archivado | Error 409 con el mensaje de que el proyecto está archivado. |
| EB-07 | Tarea sin responsables que se vence | No hay a quién notificar; se avisa únicamente al líder del proyecto. |
| EB-08 | Fallo del proveedor de correo | Se registra el fallo, se reintenta hasta 3 veces con espera creciente y la notificación dentro de la aplicación se entrega de todos modos. El fallo del correo nunca bloquea la operación que lo originó. |
| EB-09 | El proceso programado no se ejecuta un día | Al día siguiente se envían los avisos correspondientes a ese día. No se reconstruyen los atrasados, para no inundar de correos. |
| EB-10 | Fecha límite en el pasado al crear la tarea | Se permite con una advertencia visible. Puede ser una tarea que se registra tarde. |
| EB-11 | Último administrador intenta degradarse o desactivarse | Error 409, operación rechazada. |
| EB-12 | URL de entrega con formato inválido | Error de validación indicando el formato esperado. |
| EB-13 | Backend suspendido (arranque en frío) | Ver RNF-02. Nunca se muestra un error genérico ni una pantalla en blanco. |
| EB-14 | Token de acceso vencido durante el uso | El frontend renueva con el token de refresco de forma transparente. Si el refresco falla, se redirige al inicio de sesión conservando la ruta destino. |

---

## 7. Reglas de negocio de referencia

Las reglas completas, el catálogo de permisos y la matriz de estados están en `business-rules.md`. Este documento no las duplica.

---

## 8. Stack y despliegue

| Capa | Decisión |
|---|---|
| Frontend | Angular (componentes standalone, signals), Tailwind CSS, Impeccable como capa de diseño |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.x, Alembic, Pydantic v2 |
| Base de datos | PostgreSQL en Supabase (solo como base de datos gestionada; no se usan Supabase Auth, Storage ni RLS) |
| Autenticación | Propia, con JWT emitidos por FastAPI |
| Correo | Resend, remitente en `send.<dominio>` |
| Proceso programado | GitHub Actions con cron, invocando un endpoint interno protegido |
| Despliegue frontend | Cloudflare Pages o Vercel (compilación estática) |
| Despliegue backend | Render (plan gratuito) |

El detalle está en `architecture.md`.

---

## 9. Fuera de alcance

Explícitamente **no** se construye en la versión 1:

- Tareas recurrentes generadas automáticamente (la periodicidad es solo una etiqueta)
- Carga y almacenamiento de archivos
- Bitácora de auditoría completa
- Progreso o certificaciones de lecciones
- Sprints, estimaciones, puntos de historia, gráficos de avance
- Integración bidireccional con GitHub (webhooks, estado de commits)
- Notificaciones push o por WhatsApp
- Multi-semillero o multi-institución
- Modo sin conexión
- Renderizado de notebooks o PDF dentro de la aplicación
- Verificación de correo en el registro (el enlace de invitación ya prueba control de la cuenta)
