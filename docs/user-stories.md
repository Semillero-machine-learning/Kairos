# Historias de usuario y criterios de aceptación

Escritas en Gherkin para que sirvan directamente como base de las pruebas de integración. Cada historia referencia los requisitos del `PRD.md` que cubre.

---

## Épica 1 — Acceso a la plataforma

### HU-01 — Invitar a un nuevo integrante
> Como Administrador, quiero invitar a alguien por correo, para que pueda crear su cuenta sin que el registro esté abierto al público.

Cubre: RF-01, RF-02, RF-04.

```gherkin
Escenario: Invitación exitosa
  Dado que estoy autenticado como Administrador
  Y no existe ninguna cuenta con el correo "ana@ejemplo.com"
  Cuando invito a "ana@ejemplo.com" con rol global "MEMBER"
  Entonces se crea una invitación en estado "PENDING" con vigencia de 7 días
  Y se envía un correo con el enlace de invitación
  Y la respuesta incluye la URL de invitación para copiarla

Escenario: El correo ya tiene cuenta
  Dado que existe una cuenta con el correo "ana@ejemplo.com"
  Cuando invito a "ana@ejemplo.com"
  Entonces recibo un error 409 con el código "EMAIL_ALREADY_REGISTERED"

Escenario: Segunda invitación al mismo correo pendiente
  Dado que existe una invitación pendiente para "ana@ejemplo.com"
  Cuando invito nuevamente a "ana@ejemplo.com"
  Entonces la invitación anterior queda revocada
  Y se genera un token nuevo
  Y el enlace anterior deja de funcionar

Escenario: Un miembro intenta invitar
  Dado que estoy autenticado con rol global "MEMBER"
  Cuando intento crear una invitación
  Entonces recibo un error 403
```

### HU-02 — Aceptar la invitación
> Como persona invitada, quiero abrir el enlace y definir mi contraseña, para entrar a la plataforma.

Cubre: RF-03, EB-01.

```gherkin
Escenario: Aceptación exitosa
  Dado que tengo un enlace de invitación válido para "ana@ejemplo.com"
  Cuando abro el enlace
  Entonces veo mi correo precargado y no editable
  Cuando envío el nombre "Ana Gómez" y una contraseña de 12 caracteres
  Entonces se crea mi cuenta con rol global "MEMBER" y estado "ACTIVE"
  Y la invitación queda en estado "ACCEPTED"
  Y el token deja de ser válido
  Y quedo autenticado automáticamente

Escenario: Token vencido
  Dado que tengo un enlace de invitación emitido hace 8 días
  Cuando lo abro
  Entonces veo un mensaje que indica que la invitación expiró
  Y se me sugiere solicitar una nueva al administrador
  Y no se revela si el correo ya tiene cuenta

Escenario: Contraseña demasiado corta
  Cuando envío una contraseña de 6 caracteres
  Entonces recibo un error de validación indicando el mínimo de 10 caracteres
  Y la cuenta no se crea
```

### HU-03 — Recuperar la contraseña
> Como usuario, quiero restablecer mi contraseña por correo, para no depender del administrador si la olvido.

Cubre: RF-07, RN-41, RN-42.

```gherkin
Escenario: Solicitud con correo registrado
  Cuando solicito el restablecimiento para "ana@ejemplo.com"
  Entonces recibo una respuesta 202
  Y se envía un correo con un enlace de vigencia de 1 hora

Escenario: Solicitud con correo inexistente
  Cuando solicito el restablecimiento para "nadie@ejemplo.com"
  Entonces recibo exactamente la misma respuesta 202
  Y no se envía ningún correo

Escenario: Confirmación exitosa
  Dado que tengo un token de restablecimiento válido
  Cuando defino una contraseña nueva
  Entonces puedo iniciar sesión con ella
  Y todas mis sesiones anteriores quedan revocadas
  Y el token no se puede volver a usar
```

---

## Épica 2 — Proyectos y roles

### HU-04 — Crear un proyecto
> Como Administrador, quiero crear un proyecto y designar su líder, para que esa persona lo gestione con autonomía.

Cubre: RF-13, RF-14, RN-13.

```gherkin
Escenario: Creación exitosa
  Dado que estoy autenticado como Administrador
  Y existe el usuario activo "Carlos"
  Cuando creo el proyecto "Detección de anomalías" con líder "Carlos"
  Entonces el proyecto queda en estado "ACTIVE"
  Y existen tres roles de proyecto: "Líder", "Colaborador" y "Observador"
  Y los tres están marcados como roles del sistema
  Y "Carlos" es miembro con el rol "Líder"
  Y el rol "Líder" tiene los 14 permisos del catálogo

Escenario: Un líder de otro proyecto intenta crear uno nuevo
  Dado que soy líder del proyecto "Visión por computador" con rol global "MEMBER"
  Cuando intento crear un proyecto
  Entonces recibo un error 403
```

### HU-05 — Crear un rol a la medida
> Como líder de proyecto, quiero crear roles con permisos específicos, para dar acceso preciso sin repartir privilegios de más.

Cubre: RF-21, RF-22, RF-23, RN-05, RN-19.

```gherkin
Escenario: Creación exitosa
  Dado que soy líder del proyecto "Detección de anomalías"
  Cuando creo el rol "Revisor" en color "#B8860B"
  Y le asigno los permisos "task.view", "task.comment" y "task.review"
  Entonces el rol queda creado dentro de ese proyecto
  Y queda registrado que yo lo creé y en qué fecha
  Y el rol no aparece en ningún otro proyecto

Escenario: Rol sin el permiso de ver
  Cuando creo un rol con los permisos "task.review" y "task.comment" solamente
  Entonces recibo un error de validación
  Y se me indica que "task.view" es obligatorio

Escenario: Nombre repetido
  Dado que ya existe el rol "Revisor" en el proyecto
  Cuando creo otro llamado "revisor"
  Entonces recibo un error 409 con el código "ROLE_NAME_TAKEN"

Escenario: Editar un rol del sistema
  Cuando intento cambiar los permisos del rol "Líder"
  Entonces recibo un error 409 con el código "SYSTEM_ROLE_IMMUTABLE"

Escenario: Borrar un rol con miembros
  Dado que el rol "Revisor" tiene 2 miembros asignados
  Cuando intento eliminarlo
  Entonces recibo un error 409 indicando que tiene 2 miembros asignados

Escenario: El cambio de permisos aplica de inmediato
  Dado que "Ana" tiene el rol "Revisor" y una sesión abierta
  Cuando le quito el permiso "task.review" al rol
  Entonces la siguiente petición de Ana para aprobar una entrega es rechazada
  Y no hace falta que vuelva a iniciar sesión
```

### HU-06 — Aislamiento entre proyectos
> Como integrante, quiero que mis privilegios en un proyecto no se filtren a otro, para que la delegación sea segura.

Cubre: RN-04.

```gherkin
Escenario: Líder en un proyecto, colaborador en otro
  Dado que soy "Líder" del proyecto A y "Colaborador" del proyecto B
  Cuando intento crear una tarea en el proyecto A
  Entonces la operación tiene éxito
  Cuando intento crear una tarea en el proyecto B
  Entonces recibo un error 403

Escenario: Proyecto ajeno
  Dado que no soy miembro del proyecto C
  Cuando solicito el detalle del proyecto C
  Entonces recibo un error 404 y no un 403
```

---

## Épica 3 — Ciclo de vida de las tareas

### HU-07 — Crear y asignar una tarea
> Como líder, quiero crear tareas con responsables y fecha límite, para repartir el trabajo con claridad.

Cubre: RF-25, RF-26, RF-27, RF-39.

```gherkin
Escenario: Creación con dos responsables
  Dado que soy líder del proyecto
  Cuando creo la tarea "Entrenar el modelo base" con periodicidad "WEEKLY",
       fecha límite "2026-09-20" y responsables "Ana" y "Luis"
  Entonces la tarea queda en estado "BACKLOG"
  Y "Ana" y "Luis" reciben una notificación en la aplicación
  Y ambos reciben un correo con el título, el proyecto y la fecha límite

Escenario: La periodicidad no genera tareas
  Dado que existe una tarea con periodicidad "WEEKLY" y fecha límite de la semana pasada
  Cuando pasa una semana
  Entonces no se crea ninguna tarea nueva automáticamente

Escenario: Fecha límite en el pasado
  Cuando creo una tarea con fecha límite anterior a hoy
  Entonces la tarea se crea
  Y la interfaz muestra una advertencia visible
```

### HU-08 — Trabajar y entregar
> Como responsable, quiero mover mi tarea y registrar lo que hice, para que quede constancia del trabajo.

Cubre: RF-30, RF-31, RF-32, RN-10.

```gherkin
Escenario: Mover la tarea propia sin permisos especiales
  Dado que soy responsable de una tarea en estado "TODO"
  Y mi rol solo tiene "task.view" y "task.comment"
  Cuando muevo la tarea a "IN_PROGRESS"
  Entonces la operación tiene éxito

Escenario: Mover una tarea ajena
  Dado que no soy responsable de la tarea
  Y mi rol no tiene "task.change_status_any"
  Cuando intento moverla a "IN_PROGRESS"
  Entonces recibo un error 403

Escenario: Entrega exitosa
  Dado que soy responsable de una tarea en estado "IN_PROGRESS"
  Cuando registro una entrega con la descripción de lo realizado
       y la URL "https://github.com/semillero-ml/anomalias/commit/a1b2c3d"
  Entonces la tarea pasa a "IN_REVIEW"
  Y la entrega queda en estado "PENDING"

Escenario: Pasar a revisión sin entrega
  Cuando intento mover la tarea a "IN_REVIEW" sin registrar entrega
  Entonces recibo un error 409 con el código "SUBMISSION_REQUIRED"

Escenario: URL que no es de GitHub
  Cuando registro una entrega con la URL "https://drive.google.com/archivo"
  Entonces recibo un error de validación indicando el formato esperado

Escenario: Segunda entrega mientras hay una pendiente
  Dado que la tarea ya tiene una entrega en estado "PENDING"
  Cuando intento registrar otra
  Entonces recibo un error 409 con el código "SUBMISSION_ALREADY_PENDING"

Escenario: Transición no permitida
  Dado que la tarea está en "TODO"
  Cuando intento moverla directamente a "DONE"
  Entonces recibo un error 409 con el código "INVALID_TRANSITION"
  Y el mensaje enumera las transiciones válidas desde "TODO"
```

### HU-09 — Revisar una entrega
> Como revisor, quiero aprobar o devolver el trabajo, para asegurar la calidad antes de dar la tarea por terminada.

Cubre: RF-33, RF-34, RN-07, RN-09.

```gherkin
Escenario: Aprobación
  Dado que tengo el permiso "task.review"
  Y no soy responsable de la tarea
  Y la tarea está en "IN_REVIEW" con una entrega pendiente
  Cuando apruebo la entrega
  Entonces la tarea pasa a "DONE"
  Y se registra la fecha de finalización
  Y quien entregó recibe notificación y correo

Escenario: Devolución
  Cuando devuelvo la entrega con el comentario "Falta la evaluación en prueba"
  Entonces la tarea vuelve a "IN_PROGRESS"
  Y la entrega queda en estado "REJECTED" conservando el comentario
  Y quien entregó recibe notificación y correo

Escenario: Devolución sin comentario
  Cuando devuelvo la entrega sin comentario
  Entonces recibo un error 422 con el código "REVIEW_COMMENT_REQUIRED"

Escenario: Autoaprobación
  Dado que tengo el permiso "task.review"
  Y soy responsable de la tarea
  Cuando intento aprobar mi propia entrega
  Entonces recibo un error 403 con el código "CANNOT_REVIEW_OWN_SUBMISSION"

Escenario: Historial completo
  Dado que una tarea tuvo una entrega devuelta y luego una aprobada
  Cuando consulto sus entregas
  Entonces veo las dos, con sus fechas, revisores y comentarios
```

---

## Épica 4 — Notificaciones

### HU-10 — Recibir recordatorios de vencimiento
> Como responsable, quiero que me avisen antes de que venza mi tarea, para no pasarme de la fecha.

Cubre: RF-40, RF-41, RF-44, RN-27, RN-28.

```gherkin
Escenario: Aviso previo
  Dado que la configuración global tiene los días de aviso [3, 1, 0]
  Y existe una tarea en "IN_PROGRESS" que vence en 3 días
  Cuando se ejecuta el proceso programado
  Entonces cada responsable activo recibe notificación y correo
  Y se registra el despacho con la fecha de hoy

Escenario: Idempotencia
  Dado que el proceso ya se ejecutó hoy y envió los avisos
  Cuando se ejecuta de nuevo el mismo día
  Entonces no se envía ningún correo duplicado
  Y el resumen reporta los despachos omitidos

Escenario: Tarea vencida
  Dado que una tarea venció ayer y no está en "DONE"
  Y los avisos de vencidas están habilitados
  Cuando se ejecuta el proceso
  Entonces los responsables reciben el aviso
  Y también lo reciben los miembros con el permiso "task.review"

Escenario: Tarea vencida sin responsables
  Dado que una tarea vencida no tiene responsables
  Cuando se ejecuta el proceso
  Entonces solo se notifica a quienes tienen "task.review"

Escenario: Proyecto archivado
  Dado que el proyecto de la tarea está archivado
  Cuando se ejecuta el proceso
  Entonces no se envía ninguna notificación de esa tarea

Escenario: Usuario desactivado
  Dado que un responsable está desactivado
  Cuando se ejecuta el proceso
  Entonces no recibe ninguna notificación

Escenario: Fallo del proveedor de correo
  Dado que Resend devuelve un error
  Cuando se intenta el envío
  Entonces se reintenta hasta 3 veces
  Y la notificación dentro de la aplicación se crea de todos modos
  Y el despacho queda registrado como fallido
```

### HU-11 — Configurar los recordatorios
> Como Administrador, quiero definir cuándo se envían los avisos, para ajustarlos al ritmo del semillero.

Cubre: RF-43, RN-26.

```gherkin
Escenario: Cambio de configuración
  Dado que estoy autenticado como Administrador
  Cuando cambio los días de aviso a [5, 2] y la hora de envío a las 8
  Entonces la configuración queda guardada
  Y aplica a todos los proyectos por igual

Escenario: Un líder intenta configurar
  Dado que soy líder de un proyecto pero mi rol global es "MEMBER"
  Cuando intento modificar la configuración de notificaciones
  Entonces recibo un error 403

Escenario: Valores inválidos
  Cuando envío una hora de envío de 25
  Entonces recibo un error de validación
```

---

## Épica 5 — Lecciones

### HU-12 — Publicar material de estudio
> Como Editor de Lecciones, quiero organizar el material en módulos y lecciones, para que el semillero encuentre todo en un solo lugar.

Cubre: RF-46 a RF-51, RN-31, RN-33.

```gherkin
Escenario: Creación en borrador
  Dado que tengo el rol global "LESSON_EDITOR"
  Cuando creo el módulo "Redes neuronales"
  Entonces queda en estado borrador
  Y no es visible para los usuarios con rol "MEMBER"

Escenario: Publicación
  Dado que el módulo tiene 3 lecciones publicadas
  Cuando publico el módulo
  Entonces todos los usuarios autenticados pueden verlo

Escenario: Lección publicada dentro de módulo en borrador
  Dado que el módulo está en borrador
  Y contiene una lección publicada
  Cuando un usuario con rol "MEMBER" consulta el catálogo
  Entonces no ve ni el módulo ni la lección

Escenario: Un líder de proyecto intenta publicar
  Dado que soy líder de un proyecto con rol global "MEMBER"
  Cuando intento crear un módulo de lecciones
  Entonces recibo un error 403

Escenario: Recursos enlazados
  Cuando agrego a una lección un recurso de tipo "NOTEBOOK"
       con la URL del repositorio del semillero
  Entonces el recurso queda enlazado
  Y no se almacena ningún archivo en la plataforma

Escenario: Eliminación de módulo con contenido
  Dado que el módulo tiene 3 lecciones
  Cuando intento eliminarlo sin confirmación
  Entonces recibo un error 409 indicando que se perderían 3 lecciones
```

---

## Épica 6 — Archivado e historial

### HU-13 — Archivar un proyecto terminado
> Como líder, quiero archivar el proyecto al terminarlo, para que deje de generar ruido sin perder lo que se hizo.

Cubre: RF-18, RN-15, RN-16, EB-06.

```gherkin
Escenario: Archivado
  Dado que tengo el permiso "project.archive"
  Cuando archivo el proyecto
  Entonces queda en estado "ARCHIVED" con su fecha de archivado
  Y desaparece de la lista de proyectos activos
  Y sigue siendo consultable con todas sus tareas y entregas

Escenario: Escritura sobre proyecto archivado
  Dado que el proyecto está archivado
  Cuando intento crear una tarea, comentar o agregar un miembro
  Entonces cada intento devuelve un error 409 con el código "PROJECT_ARCHIVED"

Escenario: Desarchivado
  Cuando desarchivo el proyecto
  Entonces vuelve a estado "ACTIVE"
  Y las notificaciones se reanudan
```

---

## Épica 7 — Experiencia en dispositivos

### HU-14 — Usar la plataforma desde el teléfono
> Como integrante, quiero consultar y actualizar mis tareas desde el celular, porque no siempre estoy frente al computador.

Cubre: RNF-01, RNF-02.

```gherkin
Escenario: Tablero en móvil
  Dado que abro un proyecto en una pantalla de 360 px de ancho
  Entonces veo la vista de lista agrupada por estado
  Y cada tarea tiene un selector para cambiar de estado
  Y no hay arrastrar y soltar

Escenario: Tablero en escritorio
  Dado que abro un proyecto en una pantalla de 1440 px
  Entonces veo las cinco columnas del Kanban
  Y puedo arrastrar tareas entre columnas

Escenario: Arranque en frío
  Dado que el backend estaba suspendido
  Cuando abro la aplicación
  Y la primera petición supera los 3 segundos
  Entonces veo el mensaje de que el servidor está despertando
  Y la petición se reintenta hasta 90 segundos
  Y nunca veo una pantalla en blanco ni un error genérico
```

---

## Orden de implementación sugerido

Cada bloque deja el sistema en un estado utilizable de punta a punta:

1. HU-01, HU-02, HU-03 — sin acceso no hay nada que probar
2. HU-04, HU-06 — proyectos y aislamiento
3. HU-07, HU-08, HU-09 — el corazón del producto
4. HU-05 — roles a la medida, sobre un sistema de permisos ya en funcionamiento
5. HU-10, HU-11 — notificaciones, cuando ya hay tareas reales que recordar
6. HU-12 — lecciones, módulo independiente
7. HU-13, HU-14 — archivado y pulido de la experiencia adaptable
