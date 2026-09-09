---
version: 1
slug: "frontend-src-app"
primary_target: "frontend/src/app"
related_targets: ["frontend/src/app/features/auth","frontend/src/app/features/admin","frontend/src/app/features/projects","frontend/src/app/features/lessons","frontend/src/app/core/layout"]
---

Ámbito: toda la aplicación autenticada (Fases 1 a 6). Fase 1: ingreso, aceptar invitación, recuperar contraseña, perfil, usuarios, invitaciones, más el armazón autenticado. Fase 2: lista de proyectos con su formulario de creación, armazón del proyecto con tres pestañas, resumen, miembros y editor de roles. Fases 3 y 4: tablero Kanban con su tarjeta, detalle de tarea, editor, comentarios y entregas, más «Mis tareas». Fase 5: campana de notificaciones y configuración global de recordatorios. Fase 6: catálogo de lecciones, detalle de lección, editor de módulos y editor de lecciones con sus recursos. Modo: Operate.

**Pendiente de auditoría, y es deuda acumulada.** De las pantallas de arriba, solo las de la Fase 1 pasaron por `audit` y tienen capturas en `review/`. Todo lo demás se construyó dentro del contrato de dirección de abajo y `detect` lo da limpio (0 anti-patrones), pero ninguna pasó por `shape` antes ni por `audit` y `polish` después:

| Pantallas | Estado |
|---|---|
| Fase 1 | Auditadas, con capturas |
| Fase 2 — `features/projects` | Solo `detect` |
| Fases 3 y 4 — `features/projects/board` | Solo `detect` |
| Fase 5 — `core/layout/notification-bell`, `features/admin/notification-settings` | Solo `detect` |
| Fase 6 — `features/lessons` | Solo `detect` |

Saldarlo es el trabajo de la Fase 7 del roadmap, que existe para eso. Cada auditoría deja sus capturas en `review/` con el nombre de la pantalla y el tamaño.

Audiencia: ~50 estudiantes de un semillero de ML y 1–2 coordinadores. Tarea: entrar, y saber qué se debe y para cuándo. Restricciones: español, AA, 360 px en adelante, áreas táctiles de 44 px, arranque en frío visible.

Sin decisiones abiertas. El logo llegó y está en `frontend/logo/kairos_logo.jpeg`; los assets con transparencia derivados viven en `frontend/public/brand/` con su procedencia documentada al lado.

## Direction contract

THESIS: KAIROS entrega el estándar de la categoría, jugado en serio y sin ironía. Lo que posee es la calma: nada que aprender antes de trabajar. Rechaza el mundo-metáfora (instrumento, bitácora) que la tirada ofreció; el usuario tomó la salida permanente a propósito.

OWN-WORLD: fondo blanco cálido levemente entintado de violeta, jamás gris puro. Bordes de un pelo en vez de sombras. Figtree en una sola familia, con numerales tabulares. Violeta de marca como único acento; magenta reservado para lo destructivo. Aire generoso, escala de 8. Sin tarjeta dentro de tarjeta, sin degradados en superficie.

STORY: la persona invitada entiende que la esperaban, define su contraseña y entra. El administrador ve quién entró y quién sigue pendiente.

FIRST VIEWPORT: ingreso. Columna única centrada de 380 px sobre el fondo liso, sin tarjeta flotante. Logo arriba, dos campos, un botón primario de ancho completo. "¿Olvidaste tu contraseña?" como enlace discreto debajo. El aviso de arranque en frío entra fijo en el borde superior, empujando, sin tapar.

FORM: canon (el estándar de la categoría), tomado como salida permanente de la ronda de dirección; puesto 0 de la lista propia por elección explícita del usuario. Semilla 8b6cc922. Listón de acabado: Notion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
