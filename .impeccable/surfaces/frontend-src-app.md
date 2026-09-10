---
version: 1
slug: "frontend-src-app"
primary_target: "frontend/src/app"
related_targets: ["frontend/src/app/features/auth","frontend/src/app/features/admin","frontend/src/app/features/projects","frontend/src/app/features/lessons","frontend/src/app/core/layout"]
---

Ámbito: toda la aplicación autenticada (Fases 1 a 6). Fase 1: ingreso, aceptar invitación, recuperar contraseña, perfil, usuarios, invitaciones, más el armazón autenticado. Fase 2: lista de proyectos con su formulario de creación, armazón del proyecto con tres pestañas, resumen, miembros y editor de roles. Fases 3 y 4: tablero Kanban con su tarjeta, detalle de tarea, editor, comentarios y entregas, más «Mis tareas». Fase 5: campana de notificaciones y configuración global de recordatorios. Fase 6: catálogo de lecciones, detalle de lección, editor de módulos y editor de lecciones con sus recursos. Modo: Operate.

**Auditada en la Fase 7.** Las pantallas de la Fase 1 ya venían auditadas
desde su fase. El resto se revisó en la auditoría de la Fase 7, a 1440 y a
360 px, con las capturas en `review/`. `detect` sigue dando 0 anti-patrones.

| Pantallas | Estado |
|---|---|
| Fase 1 | Auditadas en su fase, con capturas |
| Fase 2 — `features/projects` | Auditadas: lista, resumen, miembros y roles |
| Fases 3 y 4 — `features/projects/board` | Auditadas: tablero, tarjeta, detalle, entregas |
| Fase 5 — `core/layout/notification-bell`, `features/admin/notification-settings` | Campana auditada (geometría a 360 comprobada); configuración, pasada ligera |
| Fase 6 — `features/lessons` | Catálogo y detalle auditados; los dos editores, pasada ligera |

El alcance se recortó a propósito: auditoría completa a lo que se usa a diario
y es difícil, y pasada ligera —360 px y `detect`— a lo que tocan una o dos
personas de vez en cuando (editor de roles, configuración de notificaciones,
editores de lecciones).

### Lo que encontró y cómo quedó

| Hallazgo | Estado |
|---|---|
| Toda fecha límite se mostraba un día antes: `new Date('2026-07-31')` es medianoche UTC y en Bogotá (−5) cae en el 30 | Corregido en `bogota-date.pipe.ts`, con su prueba |
| El tablero ofrecía arrastrar por debajo de 768 px, donde las columnas están apiladas | Corregido: puntero preciso **y** ancho, en una media query reactiva |
| `ink-faint` no llega a AA como color de texto (3.09:1 en el catálogo) | Corregido: los diez usos de contenido pasan a `ink-muted`; el token se queda en los deshabilitados |
| El título de la tarjeta, único interactivo sin variante táctil (20 px) | Corregido con relleno y margen negativo, sin cambiar el alto de la tarjeta |
| `create_admin` creaba administradores con un correo que el login rechaza | Corregido en el servicio, con el mismo validador de los esquemas |
| La sonda del servidor vivía en el inicio de todos los miembros | Quitada, por decisión del equipo |
| El estado vacío del primer día llevaba a otro estado vacío | El botón apunta al catálogo cuando no hay proyectos |

Comprobado y correcto, sin cambios: contraste AA en siete pantallas (0 fallos
tras la corrección), ausencia de desbordes horizontales a 360 px, el diálogo de
tarea como `<dialog>` modal nativo (foco atrapado y Escape), la campana dentro
de la ventana a 360, los 44 px táctiles del resto del sistema —que ya venían
resueltos con `any-pointer-coarse`—, el arranque en frío de punta a punta (aviso
a los 3 s, mensaje honesto a los 90) y las dos pantallas de error, que además no
delatan si un proyecto ajeno existe.

Descartado tras verificar: el aviso «Tu sesión terminó» en una visita limpia era
una sesión vieja del perfil de Chrome caducando correctamente.

Audiencia: ~50 estudiantes de un semillero de ML y 1–2 coordinadores. Tarea: entrar, y saber qué se debe y para cuándo. Restricciones: español, AA, 360 px en adelante, áreas táctiles de 44 px, arranque en frío visible.

Sin decisiones abiertas. El logo llegó y está en `frontend/logo/kairos_logo.jpeg`; los assets con transparencia derivados viven en `frontend/public/brand/` con su procedencia documentada al lado.

## Direction contract

THESIS: KAIROS entrega el estándar de la categoría, jugado en serio y sin ironía. Lo que posee es la calma: nada que aprender antes de trabajar. Rechaza el mundo-metáfora (instrumento, bitácora) que la tirada ofreció; el usuario tomó la salida permanente a propósito.

OWN-WORLD: fondo blanco cálido levemente entintado de violeta, jamás gris puro. Bordes de un pelo en vez de sombras. Figtree en una sola familia, con numerales tabulares. Violeta de marca como único acento; magenta reservado para lo destructivo. Aire generoso, escala de 8. Sin tarjeta dentro de tarjeta, sin degradados en superficie.

STORY: la persona invitada entiende que la esperaban, define su contraseña y entra. El administrador ve quién entró y quién sigue pendiente.

FIRST VIEWPORT: ingreso. Columna única centrada de 380 px sobre el fondo liso, sin tarjeta flotante. Logo arriba, dos campos, un botón primario de ancho completo. "¿Olvidaste tu contraseña?" como enlace discreto debajo. El aviso de arranque en frío entra fijo en el borde superior, empujando, sin tapar.

FORM: canon (el estándar de la categoría), tomado como salida permanente de la ronda de dirección; puesto 0 de la lista propia por elección explícita del usuario. Semilla 8b6cc922. Listón de acabado: Notion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
