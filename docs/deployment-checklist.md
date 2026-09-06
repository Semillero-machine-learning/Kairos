# Lista de verificación de despliegue

Pasos para provisionar la infraestructura de la Fase 0. Todo opera en planes
gratuitos; el único gasto es el dominio (RNF-03). Un agente no puede crear estas
cuentas ni comprar el dominio: este documento es la guía para que lo hagas tú.

El orden importa: la base de datos y el dominio son prerrequisitos del resto.

---

## 1. Supabase (base de datos)

1. Crea un proyecto en [supabase.com](https://supabase.com). Guarda la
   contraseña de la base de datos.
2. En **Project Settings → Database → Connection string**, copia la cadena del
   **agrupador en modo de transacción (puerto 6543)**, no la conexión directa
   del 5432 (agota las conexiones del plan gratuito).
3. Conviértela al formato de asyncpg para `DATABASE_URL`:
   ```
   postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
4. No se usan Supabase Auth, Storage ni RLS. Solo la base de datos.
5. La extensión `citext` y todo el esquema los crea `alembic upgrade head`
   (migración 0001 en adelante); no hay que ejecutar SQL a mano.

## 2. Dominio y DNS (Cloudflare)

`kairospartners.uk`, con estos registros:

| Nombre | Tipo | Destino | Propósito |
|---|---|---|---|
| `app` | CNAME | (el que dé Cloudflare Pages) | Frontend |
| `api` | CNAME | (el que dé Render) | Backend |
| `send` | los que indique Resend | — | SPF y DKIM del remitente |
| `_dmarc` | TXT | `v=DMARC1; p=none; rua=mailto:tu-correo@dominio` | **A mano**, Resend no lo crea |

## 3. Resend (correo)

1. Crea la cuenta y verifica el subdominio `send.kairospartners.uk` con los
   registros SPF/DKIM que indique.
2. Genera una API key para `RESEND_API_KEY`.
3. El remitente es `EMAIL_FROM`. Calienta el envío con volumen bajo al inicio
   para no caer en spam.

## 4. Render (backend)

1. Conecta el repositorio. El [`render.yaml`](../render.yaml) de la raíz define
   el servicio `kairos-api` (plan gratuito).
2. Variables de entorno (las marcadas `sync: false` se cargan a mano):
   - `DATABASE_URL` — el agrupador 6543 del paso 1.
   - `RESEND_API_KEY` — del paso 3.
   - `JWT_SECRET` y `JOB_TOKEN` — Render los genera (`generateValue`).
   - El resto tiene valores por defecto en `render.yaml`; ajusta `CORS_ORIGINS`
     y `FRONTEND_URL` al dominio real.
3. El arranque ejecuta `alembic upgrade head` y luego uvicorn.
4. `healthCheckPath` es `/health`.
5. Añade el dominio `api.kairospartners.uk` en la configuración del servicio.

## 5. Cloudflare Pages (frontend)

Se conecta cuando exista el frontend (Fase 1 en adelante). Compilación estática,
dominio `app.kairospartners.uk`.

## 6. Proceso programado (GitHub Actions)

Los flujos de recordatorios y de mantenimiento (`keepalive`) se añaden en la
Fase 5, cuando exista el endpoint `/internal/jobs/reminders`. Requieren los
secretos `API_URL` y `JOB_TOKEN` en el repositorio.

---

## Cierre de la Fase 0

El frontend desplegado consulta `GET /health` del backend desplegado y muestra
el resultado. Verifícalo abriendo `https://api.kairospartners.uk/health`, que
debe responder `{"status":"ok"}`.
