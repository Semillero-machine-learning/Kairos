# Plan de implementación

Ocho fases ordenadas por dependencia. Cada una deja el sistema funcionando de punta a punta, para que se pueda probar de verdad antes de seguir. Equipo de cuatro personas; las fases 3 y 4 se pueden repartir en paralelo.

---

## Fase 0 — Cimientos

**Backend**
- Estructura de carpetas de `architecture.md` §2
- `core/config.py`, `core/database.py`, `core/exceptions.py` con sus manejadores
- Conexión a Supabase por el agrupador (puerto 6543, `statement_cache_size=0`)
- Alembic funcionando
- Endpoint `/health` con `SELECT 1`
- Migración inicial: `permissions` (14 registros) y `notification_settings` (fila única)
- Comando `create_admin`

**Frontend**
- Proyecto Angular con componentes standalone y Tailwind
- `npx impeccable install` y `/impeccable init`
- Estructura de rutas y esqueleto general
- Interceptor HTTP con la lógica de arranque en frío

**Infraestructura**
- Proyecto en Supabase
- Servicio en Render conectado al repositorio
- Cloudflare Pages conectado
- Dominio, con `app`, `api`, `send` y `_dmarc` configurados
- Dominio verificado en Resend

**Cierre:** el frontend desplegado consulta `/health` del backend desplegado y muestra el resultado.

---

## Fase 1 — Acceso

Historias: HU-01, HU-02, HU-03.
Requisitos: RF-01 a RF-12.

- Modelos `users`, `invitations`, `refresh_tokens`, `password_reset_tokens`
- Hash con Argon2, emisión de JWT, rotación del token de refresco
- Todos los endpoints de `/auth`, `/users` e `/invitations`
- Integración con Resend y plantillas de invitación y restablecimiento
- Pantallas: ingreso, aceptar invitación, recuperar contraseña, perfil
- Administración de usuarios e invitaciones
- Guardas de ruta y renovación transparente del token

**Cierre:** un administrador invita a alguien, esa persona recibe el correo, crea su cuenta y entra. Recuperar contraseña funciona.

---

## Fase 2 — Proyectos, roles y permisos

Historias: HU-04, HU-05, HU-06.
Requisitos: RF-13 a RF-24.

- Modelos `projects`, `project_roles`, `project_role_permissions`, `project_members`
- Creación de proyecto con generación de los tres roles predeterminados en una transacción
- Dependencia `require_project_permission` con la comprobación de archivado incluida
- Gestión de miembros y roles a la medida
- Pantallas: lista de proyectos, detalle, miembros, editor de roles con selección de permisos

**Cierre:** un administrador crea un proyecto, el líder agrega miembros, crea un rol a la medida y comprueba que un usuario con ese rol solo puede hacer lo que le corresponde. Es la fase más delicada; conviene probarla a fondo antes de seguir.

---

## Fase 3 — Tareas

Historias: HU-07, HU-08.
Requisitos: RF-25 a RF-32, RF-36, RF-37.

- Modelos `tasks`, `task_assignees`
- Máquina de estados con validación de transiciones
- Endpoints de tareas y de asignación
- Tablero Kanban con arrastrar y soltar en escritorio y lista con selector en móvil
- Vista "Mis tareas" entre proyectos
- Filtros

**Cierre:** el ciclo completo de una tarea funciona salvo la revisión.

---

## Fase 4 — Entregas, revisión y comentarios

Historias: HU-09.
Requisitos: RF-31, RF-33, RF-34, RF-35.

- Modelos `task_submissions`, `task_comments`
- Registro de entrega con validación de la URL de GitHub
- Aprobación y devolución, con la prohibición de autoaprobarse
- Historial de entregas y hilo de comentarios

**Cierre:** el ciclo completo de la historia HU-09 pasa, incluidos todos sus escenarios de error.

---

## Fase 5 — Notificaciones

Historias: HU-10, HU-11.
Requisitos: RF-38 a RF-45.

- Modelos `notifications`, `notification_dispatches`
- Notificaciones inmediatas por asignación y por revisión
- Trabajo programado `jobs/reminders.py` con la lógica de idempotencia
- Endpoint interno protegido con `X-Job-Token`
- Dos flujos de GitHub Actions: recordatorios diarios y mantenimiento del servicio despierto
- Campana con historial y contador de no leídas
- Pantalla de configuración global

**Cierre:** el proceso se ejecuta dos veces seguidas y no duplica ningún correo. Es el punto donde más errores sutiles aparecen; probar la idempotencia en serio.

---

## Fase 6 — Lecciones

Historias: HU-12.
Requisitos: RF-46 a RF-52.

- Modelos `lesson_modules`, `lessons`, `lesson_resources`
- Endpoints con la restricción de rol global
- Catálogo público y editor con reordenamiento

**Cierre:** el editor publica un módulo con lecciones y recursos, y los miembros lo ven. Módulo independiente: se puede desarrollar en paralelo a las fases 3 a 5.

---

## Fase 7 — Auditoría y corrección

Historias: HU-13, HU-14.
Requisitos: RF-18, RNF-01, RNF-02, RNF-09.

Última fase. No agrega funcionalidad: verifica lo construido y arregla lo que aparezca.

**El archivado ya está hecho.** Se adelantó durante la Fase 2: los endpoints
`/archive` y `/unarchive` existen, la restricción de solo lectura vive
centralizada en `require_project_permission` en vez de repetida endpoint por
endpoint, y la interfaz tiene el control en el resumen del proyecto. De HU-13
solo faltan sus pruebas Gherkin propias.

### Deuda de auditoría

`.impeccable/surfaces/frontend-src-app.md` lleva el registro de lo verificado.
Hoy dice esto:

| Pantallas | Estado |
|---|---|
| Fase 1 — ingreso, invitación, perfil, usuarios, invitaciones | Auditadas, con capturas en `.impeccable/review/` |
| Fase 2 — lista, resumen, miembros, roles | Solo `detect`; sin `shape` antes ni `audit`/`polish` después |
| Fases 3 y 4 — tablero, tarjeta, detalle, editor, comentarios, entregas | Sin auditar, ni registradas en la superficie |
| Fase 5 — campana, configuración de notificaciones | Sin auditar |
| Fase 6 — catálogo, detalle de lección, editor de módulos y lecciones | Sin auditar |

De unas quince pantallas, seis están verificadas. **Auditar lo que falta es el
grueso de esta fase**, y conviene hacerlo antes de corregir: la mitad de los
errores de una interfaz se encuentran mirándola en serio, no esperando a que
alguien los reporte.

### Trabajo

- `/impeccable audit` sobre todo lo pendiente, guardando las capturas
- `/impeccable adapt` — repaso de 360 px en adelante, con el tablero como caso difícil
- `/impeccable onboard` — estados vacíos y primer ingreso
- `/impeccable harden` — errores y casos límite
- `/impeccable polish` sobre lo que el audit señale
- Verificación del arranque en frío de punta a punta (RNF-02): 3 segundos, aviso, reintento, 90 de espera
- Pruebas Gherkin de HU-13 y HU-14, que no existen
- Corrección de los errores que aparezcan, **uno por commit**, cada uno nombrando qué rompía

### Errores conocidos

| Error | Estado |
|---|---|
| El panel de la campana se desplegaba hacia la izquierda desde la barra lateral y se cortaba contra el borde de la ventana | Corregido en `feat/fase-3-tareas` |

**Cierre:** cada pantalla tiene su auditoría y su captura, la aplicación es
usable en un teléfono de 360 px, y el arranque en frío no produce ni una
pantalla en blanco.

---

## Reparto sugerido para cuatro personas

| Fase | Reparto |
|---|---|
| 0 | Todos, es corta |
| 1 | Dos en backend, dos en frontend |
| 2 | Dos en backend (roles y permisos), dos en frontend |
| 3 y 6 | Dos personas en tareas, dos en lecciones, en paralelo |
| 4 | Dos personas |
| 5 | Dos personas, con una dedicada al trabajo programado |
| 7 | Todos: la auditoría se reparte por pantallas, y quien construyó una no debería ser quien la audita |

La fase 2 no se paraleliza: el sistema de permisos es la base de todo lo demás y conviene que salga bien la primera vez.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El arranque en frío de Render arruina la experiencia | Ping programado en horario hábil e indicador de carga honesto (RNF-02) |
| Supabase pausa el proyecto por inactividad | El mismo ping golpea la base de datos (RNF-07) |
| El cron de GitHub Actions se retrasa o se salta | Aceptable para avisos diarios; RN-29 lo contempla |
| Los correos caen en la carpeta de no deseados | Verificar el dominio, publicar DMARC, calentar el envío con volumen bajo |
| El sistema de permisos se complica de más | El catálogo es cerrado: 14 permisos, ni uno más sin decisión explícita |
| Se acaba el semestre sin terminar | Las fases 0 a 4 ya constituyen un producto útil. Las fases 5 a 7 son incrementos que se pueden postergar |
| La deuda de auditoría crece más rápido de lo que se paga | Cada fase registra sus pantallas en `.impeccable/surfaces/`; la Fase 7 salda lo acumulado y no debería volver a acumularse |
