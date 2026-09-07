# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Administrador (coordinador del semillero).** Una o dos personas. Invitan
integrantes, crean proyectos, designan líderes, ajustan la configuración de
recordatorios y publican lecciones. Entran a la plataforma para desatascar a
otros, no para trabajar en ella todo el día.

**Miembro.** El grueso de los usuarios: unos 50 estudiantes de un semillero
universitario de Machine Learning. Rol global base. Participan en los proyectos
a los que se les agregue, con los permisos que les dé su rol *dentro de cada
proyecto*. Su pregunta diaria es "¿qué tengo pendiente y para cuándo?".

**Líder de proyecto.** No es un rol global sino un rol *dentro de un proyecto*:
reparte tareas, revisa entregas y administra los miembros de ese proyecto y solo
ese. Ser líder del proyecto A no otorga nada en el proyecto B.

**Editor de Lecciones.** Rol global. Mantiene el catálogo de material de
estudio. Sin privilegios sobre proyectos.

## Product Purpose

El semillero coordina hoy sus proyectos, tareas y material de estudio por
canales informales: chats, carpetas sueltas y repositorios dispersos. De ahí
salen tres problemas concretos, y el producto existe para resolver esos tres y
nada más:

1. Nadie sabe con certeza qué tareas tiene asignadas.
2. Los vencimientos se pasan sin aviso.
3. El material de estudio está regado.

Tiene éxito si el 100% de los miembros activos tiene cuenta en las dos primeras
semanas y si bajan las tareas vencidas sin entrega respecto al semestre
anterior.

## Positioning

Un Jira reducido, deliberadamente. La diferencia no está en tener más funciones
sino en tener menos: el catálogo de permisos es cerrado (14 códigos, ni uno más
sin decisión explícita), la periodicidad es una etiqueta y no una recurrencia
real, y no hay carga de archivos porque el material ya vive en GitHub. Lo que no
sirva directamente a los tres problemas de arriba queda fuera.

El segundo eje propio son los **dos planos de roles**: roles globales fijos
(Administrador, Editor de Lecciones, Miembro) y roles de proyecto dinámicos con
permisos configurables por proyecto. Un usuario tiene exactamente un rol global
y exactamente un rol en cada proyecto del que forma parte.

## Operating Context

- **Registro cerrado.** Nadie se registra por su cuenta: se entra por invitación
  de un Administrador, con enlace de un solo uso y 7 días de vigencia. La
  primera pantalla que ve un usuario nuevo no es un formulario de registro, es
  un enlace que le llegó por correo.
- **El correo es parte del producto**, no un adorno. Invitación, restablecimiento
  de contraseña, asignación de tarea, recordatorio de vencimiento y resultado de
  revisión llegan por correo además de la campana dentro de la aplicación.
- **Semestre académico.** El ritmo de uso sube y baja con el calendario; el
  volumen previsto es de unas 1.000 tareas por semestre.
- **El trabajo real ocurre en GitHub.** Una entrega es una descripción más,
  opcionalmente, la URL de un commit o pull request. La plataforma coordina y
  recuerda; no aloja nada.
- **Uso repartido entre computador y teléfono.** Ninguno de los dos es el caso
  secundario: la misma persona revisa el tablero en el portátil y consulta un
  vencimiento desde el celular. Confirmado por el usuario.
- **Infraestructura gratuita, con las consecuencias visibles.** El backend se
  suspende tras unos 15 minutos sin tráfico y la primera petición puede tardar
  cerca de un minuto. Es una condición de uso, no un caso raro: la interfaz
  tiene que responder por ella con honestidad ("Despertando el servidor..."),
  nunca con una pantalla en blanco.

## Capabilities and Constraints

**Lo que hace**

- Invitaciones, cuentas, roles globales, activación y desactivación de usuarios.
- Proyectos con miembros y roles de proyecto configurables.
- Tareas con responsables, fecha límite, periodicidad como etiqueta, y cinco
  estados fijos: `BACKLOG` → `TODO` → `IN_PROGRESS` → `IN_REVIEW` → `DONE`.
- Tablero Kanban, vista personal "Mis tareas" entre proyectos, y filtros.
- Entregas con revisión (aprobar o devolver con comentario obligatorio) e
  historial completo, más comentarios por tarea.
- Notificaciones por dos canales: campana con historial y contador de no leídas,
  y correo.
- Catálogo de lecciones en módulos, lecciones y recursos, con estado borrador o
  publicado.

**Lo que no hace, por decisión**

- No genera tareas recurrentes automáticamente. La periodicidad es descriptiva.
- No aloja archivos. Solo enlaza a GitHub y otras fuentes.
- No lleva bitácora de auditoría ni progreso por usuario en las lecciones.
- No elimina usuarios ni proyectos: se desactivan y se archivan.
- Un proyecto archivado es de solo lectura, completo y consultable.

**Restricciones técnicas**

- Toda autorización se verifica en el backend. La interfaz oculta lo que el
  usuario no puede hacer, pero eso es comodidad, nunca la barrera.
- Costo de operación de 0 USD/mes: planes gratuitos de Supabase, Render,
  Cloudflare Pages, GitHub Actions y Resend. El único gasto es el dominio.
- Escala objetivo modesta: 50 usuarios, 10 proyectos activos.
- Las marcas de tiempo se guardan en UTC y se presentan en `America/Bogota`.

**Terminología** (la que ve el usuario, en español)

Proyecto, tarea, entrega, revisión, responsable, miembro, rol, permiso, módulo,
lección, recurso, periodicidad (Puntual, Semanal, Mensual, Semestral).

## Brand Commitments

- **Nombre visible: KAIROS.** Es el que va en la barra superior, el título de la
  pestaña y los correos. Confirmado por el usuario.
- **Logo existente y vinculante:** un monograma "K" de trazo continuo (monoline,
  extremos redondeados, con un nodo circular en el punto de unión) sobre el
  logotipo "KAIROS" en una geométrica de peso ligero y letterspacing amplio. El
  monograma y el logotipo comparten un degradado horizontal que va de un azul
  violeta a un magenta.
- **El degradado pertenece a la marca, no a la interfaz.** `CLAUDE.md` prohíbe
  los degradados de morado a azul como anti-patrón visual, y esa prohibición
  sigue en pie para fondos, botones, tarjetas y cualquier superficie de la
  aplicación. El degradado se usa únicamente dentro del logo. La paleta de la
  interfaz se deriva de los extremos del degradado como colores **sólidos**.
- **El archivo del logo ya está en el repositorio:** `frontend/logo/kairos_logo.jpeg`
  es el original entregado por el usuario, sin modificar. De ahí salen los
  assets con transparencia de `frontend/public/brand/`, cuya derivación está
  documentada en `frontend/public/brand/PROVENANCE.md`. No se redibujó el
  monograma y no debe redibujarse: si aparece el original vectorial, se
  reemplazan esos PNG y nada más.
- **Voz:** española, directa y sin ceremonia. Los mensajes de error explican qué
  pasó y qué hacer. Los códigos de error, nombres de variables, tablas y
  endpoints van en inglés; todo lo que lee el usuario, en español.
- **Preferencia permanente de dirección visual: el estándar de la categoría.**
  Puesto ante una ronda de direcciones con mundos propios, el usuario tomó a
  propósito la salida convencional. KAIROS se ve y se comporta como una
  herramienta de trabajo conocida, sin metáfora ni mundo temático, y esa
  convención se ejecuta con acabado real, sin ironía y sin guiños colados.
- **Listón de acabado: Notion.** El usuario lo nombró como el producto al lado
  del cual KAIROS debe poder pararse: aire generoso, tipografía amable,
  densidad baja, calma. Ese es el nivel de craft contra el que se juzga cada
  pantalla, no un catálogo de funciones a copiar.

## Evidence on Hand

- Documentación de producto completa y aprobada en `docs/`: `PRD.md`,
  `business-rules.md` (fuente de verdad de permisos y transiciones),
  `data-model.md`, `architecture.md`, `api-contract.md`, `user-stories.md` con
  criterios en Gherkin, y `roadmap.md`.
- Backend funcionando: autenticación, invitaciones y administración de usuarios,
  con 45 pruebas en verde.
- Dominio propio: `kairospartners.uk` (`app`, `api`, `send`).
- **No hay** testimonios, casos de estudio, capturas de la herramienta anterior,
  métricas históricas, ni fotografías del semillero. Nada de eso debe
  fabricarse: el producto todavía no se ha usado con gente real.

## Product Principles

1. **Ante la duda, lo simple.** Entre una solución general y una concreta que
   resuelve el caso de hoy, gana la concreta. No es un clon de Jira.
2. **La pregunta que hay que responder primero es "¿qué me toca a mí y para
   cuándo?".** Toda pantalla se juzga por lo cerca que deja esa respuesta.
3. **Honestidad sobre el estado del sistema.** Infraestructura gratuita implica
   esperas; se dicen, no se disimulan. Nunca una pantalla en blanco ni un error
   genérico.
4. **El permiso manda sobre lo que se ve.** La interfaz muestra solo lo que el
   usuario puede hacer, para que no descubra sus límites a punta de errores.
5. **Nada se borra.** Usuarios que se desactivan, proyectos que se archivan,
   tareas con borrado lógico: el historial del semillero se conserva.

## Accessibility & Inclusion

- Contraste mínimo AA.
- Navegación por teclado en formularios y en el tablero Kanban.
- Etiquetas ARIA en los controles del Kanban.
- Adaptable desde 360 px de ancho. Áreas táctiles de 44x44 px como mínimo.
- Por debajo de 768 px el tablero deja de ser arrastrar y soltar y pasa a lista
  con selector de estado: en móvil el arrastre es incómodo y propenso a errores.
