# Lista de verificación de despliegue

Pasos para provisionar la infraestructura de la Fase 0. Todo opera en planes
gratuitos; el único gasto es el dominio (RNF-03). Un agente no puede crear estas
cuentas ni comprar el dominio: este documento es la guía para que lo hagas tú.

El orden importa: la base de datos y el dominio son prerrequisitos del resto.

---

## 1. Supabase (base de datos)

1. Crea un proyecto en [supabase.com](https://supabase.com), **en `us-east-1`
   (Norte de Virginia)**, para que quede junto al servicio de Render. Guarda la
   contraseña de la base.
2. No se usan Supabase Auth, Storage ni RLS. Solo la base de datos.
3. La extensión `citext` y todo el esquema los crea `alembic upgrade head`
   (migración 0001 en adelante); no hay que ejecutar SQL a mano.

### Las tres conexiones, que no son intercambiables

Este es el punto donde más tiempo se pierde. Supabase ofrece tres cadenas y la
interfaz no explica cuál sirve para qué.

| Conexión | Host y puerto | Para qué |
|---|---|---|
| **Directa** | `db.<ref>.supabase.co:5432` | **Ninguna.** Es solo IPv6: no tiene registro `A`, así que falla con `getaddrinfo failed` desde cualquier red IPv4, incluida la de Render. |
| **Agrupador de sesión** | `aws-0-<region>.pooler.supabase.com:5432` | Migraciones y DDL. Se comporta como una conexión normal. |
| **Agrupador de transacción** | `aws-0-<region>.pooler.supabase.com:6543` | **La aplicación.** Multiplexa, y por eso exige `statement_cache_size=0`. |

Dos detalles que rompen la conexión en silencio:

- **El usuario es `postgres.<ref>`, no `postgres`.** Con el usuario equivocado el
  agrupador responde `Tenant or user not found`.
- **La contraseña va codificada** dentro de la URL: `#`→`%23`, `!`→`%21`,
  `@`→`%40`, `$`→`%24`, `&`→`%26`. Sin codificar, un `@` parte la cadena y el
  cliente busca un host que no existe.

El formato final para `DATABASE_URL`:

```
postgresql+asyncpg://postgres.<ref>:<contraseña-codificada>@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Las cadenas reales viven en `backend/.env.supabase`, que `.gitignore` excluye.

---

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

## 5b. Igualar las regiones

**La API y la base deben vivir en la misma región.** Con Render en Oregón y
Supabase en São Paulo, cada consulta costaba ~350 ms y un endpoint que hace seis
consultas seguidas superaba el segundo. En la misma región cuesta ~2 ms.

El par correcto es **Render Virginia + Supabase `us-east-1` (Norte de Virginia)**.

Ninguno de los dos permite cambiar de región en sitio: hay que recrear. El orden
importa, porque el servicio nuevo necesita la base nueva.

1. **Supabase.** Crea un proyecto en `us-east-1`. El plan gratuito admite dos
   proyectos, así que puede convivir con el viejo. Copia la cadena del agrupador
   (puerto 6543) y conviértela al formato de asyncpg.
2. **Migra el esquema** apuntando el `.env` local a la base nueva:
   `uv run alembic upgrade head`. Crea las 14 filas de `permissions` y la fila de
   `notification_settings`.
3. **Recrea los administradores:** `uv run python -m app.cli create_admin`. Las
   contraseñas están cifradas y no se pueden trasladar; quien tenga cuenta
   deberá recibir una invitación nueva o restablecer su contraseña.
4. **Render.** Crea un servicio nuevo desde el mismo `render.yaml`, esta vez en
   Virginia. Carga a mano `DATABASE_URL` (la nueva) y `RESEND_API_KEY`.
   `JWT_SECRET` y `JOB_TOKEN` se regeneran solos: las sesiones abiertas mueren,
   que con tres usuarios no es problema.
5. **DNS.** El servicio nuevo tiene otro `onrender.com`. **Actualiza el CNAME de
   `api` en Cloudflare** y vuelve a añadir el dominio personalizado en Render.
   Este es el paso que se olvida y deja la API inalcanzable.
6. **Verifica** `https://api.kairospartners.uk/health` y que
   `/api/v1/permissions` devuelva 401 y no 404.
7. **Reactiva el pre-ping.** Hecho: `backend/app/core/database.py` ya lleva
   `pool_pre_ping=True` y `pool_recycle=1800`. Estaba apagado porque un viaje de
   ida y vuelta costaba ~650 ms; en la misma región cuesta milisegundos.
8. **Pausa el proyecto viejo de Supabase** en vez de borrarlo. Los proyectos
   pausados no cuentan para el límite del plan gratuito, y te deja marcha atrás
   durante unos días.

---

## 6. Proceso programado (GitHub Actions)

Los flujos de recordatorios y de mantenimiento (`keepalive`) se añaden en la
Fase 5, cuando exista el endpoint `/internal/jobs/reminders`. Requieren los
secretos `API_URL` y `JOB_TOKEN` en el repositorio.

---

## Cierre de la Fase 0 — verificado

El frontend desplegado consulta `GET /health` del backend desplegado y muestra
el resultado. Verifícalo abriendo `https://api.kairospartners.uk/health`, que
debe responder `{"status":"ok"}`.

Comprobado el 7 de septiembre de 2026: `app.kairospartners.uk` sirve el SPA con
los enlaces profundos funcionando, `api.kairospartners.uk` responde con
certificado válido, y el CORS acepta el origen del frontend.

**Si el dominio no te resuelve desde una red institucional**, no es un fallo del
despliegue: algunos cortafuegos —Palo Alto entre ellos— sinkholean dominios
recién registrados. Compruébalo con `nslookup api.kairospartners.uk`; si
responde algo terminado en `sinkhole`, es la red. Usa datos móviles.
