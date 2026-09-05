# CLAUDE.md

Instrucciones para agentes que trabajen en este repositorio. Léelas completas antes de escribir código.

---

## Qué es este proyecto

Plataforma interna de gestión para el semillero de Machine Learning: proyectos con tablero Kanban, tareas con responsables y recordatorios automáticos, y un catálogo de lecciones que enlaza material alojado en GitHub. Unos 50 usuarios, 10 proyectos activos. Debe operar íntegramente en planes gratuitos.

**No es un clon de Jira.** Cuando dudes entre una solución simple y una general, elige la simple.

## Documentos de referencia

Antes de implementar cualquier cosa, consulta:

| Documento | Contiene |
|---|---|
| `docs/PRD.md` | Requisitos numerados (RF-xx, RNF-xx), escenarios, alcance |
| `docs/business-rules.md` | **Fuente de verdad** de permisos, transiciones de estado y reglas (RN-xx) |
| `docs/data-model.md` | Tablas, restricciones, índices |
| `docs/architecture.md` | Estructura de módulos, autorización, proceso programado, despliegue |
| `docs/api-contract.md` | Endpoints, esquemas, códigos de error |
| `docs/user-stories.md` | Criterios de aceptación en Gherkin, base de las pruebas |
| `docs/roadmap.md` | Orden de implementación |

Ante contradicción entre documentos, manda `business-rules.md`.

---

## Reglas que no se negocian

1. **No inventes requisitos.** Si algo no está en la documentación, pregunta antes de implementarlo. No agregues funcionalidades "que seguro van a querer".
2. **No implementes nada de la sección "Fuera de alcance"** del PRD. En particular: nada de tareas recurrentes automáticas, carga de archivos, bitácora de auditoría ni progreso de lecciones.
3. **Toda autorización se verifica en el backend.** Ocultar un botón en el frontend no es una medida de seguridad, es una mejora de la experiencia.
4. **Los permisos no van dentro del JWT.** Se consultan por petición (RN-22). Si te ves tentado a meterlos para "ahorrar una consulta", no lo hagas.
5. **La idempotencia del proceso de recordatorios se apoya en la restricción de unicidad de la base de datos**, no en una comprobación en Python. Insertar en `notification_dispatches` con `ON CONFLICT DO NOTHING` **antes** de enviar.
6. **Nada de datos derivados en la base.** Sin columnas de conteo, sin `is_overdue` almacenado.
7. **Ningún secreto en el código.** Todo por variables de entorno, con su entrada en `.env.example`.
8. **No uses Supabase Auth, Storage ni RLS.** Supabase es únicamente PostgreSQL gestionado.
9. **Un fallo de correo nunca revierte una operación de negocio.** Se registra y se sigue.
10. **Los mensajes de error visibles van en español.** Los códigos de error, nombres de variables, tablas, endpoints y comentarios van en inglés.

---

## Estructura del repositorio

```
/
├── CLAUDE.md
├── docs/
├── backend/         # FastAPI. Ver architecture.md §2
└── frontend/        # Angular. Ver architecture.md §5
```

---

## Backend

**Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x asíncrono, Alembic, Pydantic v2, asyncpg, Argon2 (`argon2-cffi`), pytest.

### Fronteras entre capas

Se respetan estrictamente:

- `router.py` — HTTP puro. Sin consultas, sin reglas de negocio.
- `service.py` — reglas de negocio. Sin objetos HTTP, sin SQL crudo. Levanta excepciones de dominio.
- `repository.py` — consultas. Sin condiciones de negocio.
- Un módulo **no importa** el repositorio ni los modelos de otro. Usa el servicio del otro módulo.
- **No hay `relationship()` de SQLAlchemy que cruce módulos.** Solo llaves foráneas por identificador.
- Las transacciones se abren y confirman en el servicio.

### Convenciones

- Rutas en plural y minúscula: `/api/v1/projects/{project_id}/tasks`
- Esquemas Pydantic con sufijo por uso: `TaskCreate`, `TaskUpdate`, `TaskRead`
- Todos los servicios y repositorios son `async`
- Anotaciones de tipos obligatorias en firmas públicas
- Migraciones con Alembic, una por cambio, con mensaje descriptivo
- Formato y análisis estático con `ruff`

### Verificación de permisos

Siempre a través de la dependencia `require_project_permission("codigo.del.permiso")` de `app/core/dependencies.py`. **Nunca** compruebes permisos con condicionales sueltos dentro de un servicio.

Devuelve **404, no 403**, cuando el usuario no es miembro del proyecto. Un 403 confirmaría que el proyecto existe.

### Comandos

```bash
cd backend
uv sync                                  # o: pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check --fix .
uv run python -m app.cli create_admin    # primer administrador
```

---

## Frontend

**Stack:** Angular (componentes standalone, signals, sin NgModules), Tailwind CSS, Impeccable como capa de diseño.

### Impeccable manda en todo lo visual

Este proyecto usa [Impeccable](https://github.com/pbakaus/impeccable) para las decisiones de diseño.

**Antes de escribir la primera pantalla:**

```bash
npx impeccable install
# luego, dentro de Claude Code:
/impeccable init
```

`init` genera `PRODUCT.md` y configura el resto. A partir de ahí:

- Antes de construir una pantalla nueva: `/impeccable shape`
- Al terminarla: `/impeccable audit` y `/impeccable polish`
- Para la adaptación a distintos dispositivos: `/impeccable adapt`
- Para estados vacíos y primer ingreso: `/impeccable onboard`
- Para errores y casos límite: `/impeccable harden`

**Anti-patrones prohibidos** (los detecta el analizador de Impeccable, pero conócelos de antemano):

- Nada de Inter, Arial ni tipografías por defecto del sistema
- Nada de degradados de morado a azul
- Nada de tarjetas anidadas dentro de tarjetas
- Nada de texto gris sobre fondos de color
- Nada de negros ni grises puros: siempre matizados
- Nada de suavizado con rebote o elástico

No inventes tokens de diseño por tu cuenta: los define `DESIGN.md`, generado por Impeccable.

### Convenciones de Angular

- Componentes standalone. Sin NgModules.
- Estado con `signal` y `computed`. **Sin NgRx.**
- Rutas por funcionalidad con carga diferida.
- Todo el acceso HTTP pasa por servicios en `core/api/`. Ningún componente llama a `HttpClient` directamente.
- Nombres de archivo en `kebab-case`: `task-board.component.ts`
- Textos de la interfaz en español. Nombres de variables, componentes y archivos en inglés.

### Puntos de quiebre adaptables

| Ancho | Comportamiento |
|---|---|
| < 768 px | Lista por estado con selector. Sin arrastrar y soltar. |
| 768–1024 px | Columnas con desplazamiento horizontal. |
| > 1024 px | Cinco columnas visibles. |

Áreas táctiles de 44×44 px como mínimo.

### Manejo del arranque en frío

El backend en el plan gratuito de Render se suspende. Un interceptor debe emitir un evento global si una petición supera los 3 segundos, para que la interfaz muestre "Despertando el servidor...". Tiempo de espera de 90 segundos. **Nunca** un error genérico ni una pantalla en blanco.

### Comandos

```bash
cd frontend
npm install
npm start
npm run build
npm test
npx impeccable detect src/      # analizador de diseño
```

---

## Pruebas

Cobertura obligatoria, sin excepciones:

1. **Transiciones de estado de tareas** — cada transición válida e inválida de la tabla de `business-rules.md` §4
2. **Resolución de permisos** — `require_project_permission` con rol de sistema, rol a la medida, no miembro y proyecto archivado
3. **Idempotencia del proceso programado** — ejecutarlo dos veces no debe generar envíos duplicados

Las pruebas de integración se derivan de los escenarios Gherkin de `docs/user-stories.md`. Usa los mismos nombres, para poder rastrearlas.

---

## Errores frecuentes que debes evitar

| Error | Por qué importa |
|---|---|
| Meter los permisos en el JWT | Los cambios de rol no surtirían efecto (RN-22) |
| Comprobar duplicados en Python antes de insertar el despacho | Deja una ventana de carrera; la restricción de unicidad no |
| Usar `datetime.now()` sin zona horaria | Los vencimientos se calculan en `America/Bogota`; guardar en UTC |
| Devolver 403 en un proyecto ajeno | Filtra la existencia del proyecto; devolver 404 |
| Dejar que un revisor apruebe su propia entrega | Viola RN-07 |
| Olvidar la comprobación de proyecto archivado | Va centralizada en la dependencia, no repetida por endpoint |
| Conectarse a Supabase por el puerto 5432 | Agota las conexiones del plan gratuito; usar el agrupador en el 6543 con `statement_cache_size=0` |
| Modelar la periodicidad como recurrencia real | Es solo una etiqueta (RF-26) |
| Permitir varios roles por usuario en un proyecto | Es uno solo (RN-03) |

---

## Al terminar una tarea

1. Ejecuta las pruebas y el analizador estático
2. Verifica que los criterios Gherkin correspondientes pasan
3. En el frontend, ejecuta `npx impeccable detect` sobre lo que tocaste
4. Actualiza la documentación si cambiaste una regla de negocio o el contrato de la API
5. Confirma los cambios con un mensaje que referencie el requisito: `feat(tasks): revisión de entregas (RF-33, RN-07)`
