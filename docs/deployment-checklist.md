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

## 5. Cloudflare Workers (frontend)

Cloudflare dejó de ofrecer la creación de proyectos de Pages desde el panel:
**Workers & Pages → Create** siempre produce un Worker. Para un SPA es
equivalente, siempre que el Worker no tenga script propio y se limite a servir
los archivos del build. La configuración vive en
[`frontend/wrangler.jsonc`](../frontend/wrangler.jsonc).

1. **Workers & Pages → Create → Import a repository.** Conecta el repositorio.
2. Ajustes de compilación:

   | Ajuste | Valor |
   |---|---|
   | Directorio raíz | `frontend` |
   | Comando de compilación | `npm install && npm run build` |
   | Comando de despliegue | `npx wrangler deploy` |
   | Versión de Node | 22.12 o superior (variable `NODE_VERSION`) |

   El directorio de salida no se configura aquí: lo declara `assets.directory`
   en `wrangler.jsonc` (`./dist/frontend/browser`).

3. **El campo `name` de `wrangler.jsonc` debe coincidir con el nombre del Worker
   creado en el paso 1.** Si no coincide, el despliegue crea un Worker distinto y
   el dominio personalizado se queda apuntando al que ya existía.
4. El `frontend/.npmrc` fija `legacy-peer-deps=true`. No lo quites: npm 10.9.4
   falla al resolver el conjunto de pares de vitest con
   `Cannot read properties of null (reading 'edgesOut')`.
5. **No agregues un `public/_redirects`.** La reescritura del SPA ya la hace
   `not_found_handling`. Un `/* /index.html 200` junto a ella hace fallar el
   despliegue completo con `Infinite loop detected in this rule`, porque la
   regla se aplica también a su propio destino.
6. **Dominio:** en el Worker, **Settings → Domains & Routes → Add → Custom
   domain**, `app.kairospartners.uk`. Cloudflare crea el registro DNS solo; no
   hay que añadirlo a mano, y no es un CNAME visible en la zona.
7. El origen del backend está fijado en `frontend/src/environments/environment.ts`
   (`https://api.kairospartners.uk`). Si el dominio de la API cambia, se cambia
   ahí y se vuelve a compilar: no es una variable de entorno del despliegue.

---

## 6. Proceso programado (GitHub Actions)

Los flujos de recordatorios y de mantenimiento (`keepalive`) se añaden en la
Fase 5, cuando exista el endpoint `/internal/jobs/reminders`. Requieren los
secretos `API_URL` y `JOB_TOKEN` en el repositorio.

---

## Cierre de la Fase 0

El frontend desplegado consulta `GET /health` del backend desplegado y muestra
el resultado. Verifícalo abriendo `https://api.kairospartners.uk/health`, que
debe responder `{"status":"ok"}`.
