# Alcor — Sistema de Gestión de Reservas

Aplicación web full-stack para la gestión de reservas de apartamentos. Incluye un calendario visual interactivo, filtros por piso y estado, y un formulario de creación de reservas.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | Angular 19, SCSS, Signals API |
| Backend | FastAPI (Python 3), Pydantic v2 |
| Base de datos | MySQL |
| Proxy de desarrollo | Angular DevServer → `http://127.0.0.1:8000` |

---

## Estructura del proyecto

```
alcor_project/
├── backend/                  # API REST con FastAPI
│   ├── main.py               # Punto de entrada
│   ├── config.py             # Variables de entorno (Pydantic Settings)
│   ├── requirements.txt
│   ├── database/
│   │   └── connection.py     # Conexión a MySQL
│   ├── models/
│   │   └── booking.py        # Modelos Pydantic (Booking, BookingCreate, BookingUpdate)
│   ├── repositories/
│   │   └── booking_repository.py
│   ├── services/
│   │   └── booking_service.py
│   └── routers/
│       └── bookings.py       # Endpoints /api/v1/bookings
│
└── frontend/         # SPA Angular
    └── src/app/
        ├── models/           # Interfaces TypeScript (Booking, BASE_STATUSES)
        ├── services/         # BookingService (HTTP)
        ├── pipes/            # BookingColorPipe
        └── pages/
            └── calendar/     # Vista principal del calendario
                └── components/
                    ├── calendar-header/
                    ├── week-row/
                    ├── booking-modal/       # Modal de edición
                    └── booking-create-modal/ # Modal de creación
```

---

## Configuración

### 1. Variables de entorno

Copia `.env.example` a `.env` en la raíz del proyecto y rellena los valores:

```env
# Base de datos
DB_HOST=localhost
DB_PORT=3306
DB_USER=tu_usuario
DB_PASS=tu_contraseña
DB_NAME=nombre_bd
```

> También se aceptan las variantes `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_PORT`.

### 2. Base de datos y migraciones

Para una base de datos vacía, Alembic crea el esquema inicial y aplica las
migraciones pendientes:

```bash
cd backend
alembic upgrade head
```

Para desarrollo con datos reales, el dump local `db/init/backup.sql` se carga al
arrancar MySQL con Docker. Ese dump no forma parte de Git y solo se usa en local:

```bash
docker compose up db
# o, si usas Docker Compose v1:
docker-compose up db
cd backend
alembic stamp c796a5e365dc
alembic upgrade head
```

El `stamp` solo debe hacerse una vez sobre una base de datos existente creada
desde el dump. A partir de ahí, las migraciones futuras se aplican normalmente
con `alembic upgrade head`.

---

## Instalación y arranque

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./start.sh
```

La API queda disponible en `http://localhost:8000`.
Documentación interactiva: `http://localhost:8000/docs`

Para desarrollo con recarga automática:

```bash
cd backend
./start-dev.sh
```

Los scripts de arranque ejecutan primero las migraciones pendientes y, solo si
terminan correctamente, arrancan Uvicorn:

```bash
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000
```

Si hay cambios en la base de datos, crea la migración correspondiente y después
arranca la app con el script habitual:

```bash
cd backend
alembic revision --autogenerate -m "describe database change"
./start.sh
```

`python main.py` sigue arrancando la API directamente, pero no aplica
migraciones. Úsalo solo si ya has ejecutado `alembic upgrade head`.

### Frontend

```bash
cd frontend
pnpm install
pnpm start
```

La aplicación queda disponible en `http://localhost:4200`.
Las peticiones a `/api/*` se redirigen automáticamente al backend mediante el proxy configurado en `proxy.conf.json`.

### Calidad local

El hook local de commit lo gestiona `pre-commit`. Solo ejecuta checks rápidos y
autoformato sobre los archivos afectados; la validación completa vive en GitHub
Actions.

Para preparar el entorno local:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt pre-commit ruff==0.15.13 mypy==2.1.0

cd frontend
pnpm install

cd ..
pre-commit install
```

Para ejecutar los hooks manualmente desde la raíz:

```bash
pre-commit run --all-files
```

Comandos útiles para validar antes de subir:

```bash
# Backend
cd backend
ruff check .
ruff format --check .
python -m mypy api/ application/ domain/ infrastructure/ config.py main.py --config-file pyproject.toml --explicit-package-bases
alembic upgrade head
python -m pytest tests/ --cov --cov-report=term-missing

# Frontend
cd ../frontend
pnpm lint
pnpm exec prettier --check "src/**/*.{ts,html,scss}"
pnpm typecheck
pnpm test:ci
pnpm build
```

---

## API — Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/bookings/` | Listar reservas (soporta filtros por fecha) |
| `GET` | `/api/v1/bookings/{id}` | Obtener una reserva por ID |
| `POST` | `/api/v1/bookings/` | Crear nueva reserva |
| `PUT` | `/api/v1/bookings/{id}` | Actualizar reserva existente |
| `DELETE` | `/api/v1/bookings/{id}` | Eliminar reserva |

---

## Funcionalidades actuales

- **Calendario mensual** con vista de reservas por semana y carril (sin solapamientos)
- **Filtros múltiples** por piso (`apartment_id`) y estado, con checkboxes desplegables
- **Modal de detalle y edición** de reservas existentes
- **Modal de creación** de nuevas reservas con validación, cálculo automático de noches y selector de piso desde la base de datos
- **Estados de reserva**: `Confirmed`, `Pending`, `Cancelled`, `ok` (configurables en `booking.model.ts`)
- Diseño **responsive** con soporte móvil

---

## Despliegue en VPS (Docker Compose)

La producción usa **Docker Compose** con tres servicios lógicos:

| Servicio | Rol |
|---|---|
| `migrate` | Ejecuta `alembic upgrade head` una vez contra la MySQL externa |
| `backend` | FastAPI + Chromium (PDF de facturas) |
| `web` | Angular estático + Caddy (HTTPS y proxy `/api/*`) |

**No se incluye MySQL** en el stack de producción: la base de datos del cliente ya existe y solo recibe migraciones de Alembic.

Los archivos `docker-compose.yml` y `docker-compose.test.yml` de la raíz son **solo para desarrollo local y CI**.

### Requisitos en la VPS

- Docker Engine y Docker Compose v2
- DNS del dominio apuntando a la IP de la VPS (`APP_DOMAIN`)
- Puertos **80** y **443** abiertos
- Acceso de red desde la VPS a la MySQL de producción (firewall / allowlist)
- **Tailscale** instalado en el **host** de la VPS si el NAS Synology solo es accesible por red `100.x.x.x`
- Backup de la base de datos antes del primer despliegue

### Archivos de despliegue

```
alcor_properties/
├── backend/Dockerfile          # Imagen FastAPI + Chromium
├── backend/docker-entrypoint.sh
├── frontend/Dockerfile         # Build Angular + Caddy
├── deploy/Caddyfile            # TLS, proxy /api, SPA fallback
├── docker-compose.prod.yml     # Orquestación producción
├── .env.production.example     # Plantilla de variables (sin secretos)
└── .dockerignore
```

### Primer despliegue

1. Clonar el repositorio en la VPS.

2. Crear el fichero de entorno (no commitear):

```bash
cp .env.production.example .env.production
chmod 600 .env.production
# Editar .env.production con valores reales (DB, JWT, NAS, SMTP, dominio...)
```

3. Validar la configuración de Compose:

```bash
docker compose -f docker-compose.prod.yml config
```

4. Construir y levantar el stack (migraciones + backend + web):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

5. Crear el usuario administrador inicial (solo si no existe):

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/create_admin_user.py
```

6. Comprobar salud:

```bash
curl -f https://TU_DOMINIO/health
```

### Variables críticas (`.env.production`)

| Variable | Descripción |
|---|---|
| `APP_DOMAIN` | Dominio público (Caddy + certificado TLS) |
| `DB_*` | Conexión a MySQL externa |
| `JWT_SECRET_KEY` | Secreto fuerte para tokens |
| `DEFAULT_PASSWORD` | Obligatoria para arrancar la API |
| `FRONTEND_URL` | URL HTTPS del frontend (emails de reset) |
| `CORS_ORIGINS` | JSON con el origen HTTPS del frontend |
| `NAS_*` | Credenciales y ruta del NAS (PDF de facturas) |
| `BILL_PDF_CHROMIUM_PATH` | `/usr/bin/chromium` (ya en la imagen) |
| `SMTP_*` | Envío de emails en producción |

### Actualización / rollback

**Actualizar** tras un `git pull`:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

El servicio `migrate` vuelve a ejecutar `alembic upgrade head` en cada despliegue.

**Rollback** de aplicación (sin tocar la BD):

```bash
git checkout <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
```

Si una migración ya se aplicó, el rollback de código puede requerir restaurar un backup de MySQL.

### Logs y operación

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f bill-docs-retry
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml ps
```

El servicio `bill-docs-retry` reintenta cada hora la sincronización de PDFs con el NAS
(documentos en error/pendientes, intentos `Procesando` cortados y facturas sin documento).
Para forzar un ciclo manual:

```bash
docker compose -f docker-compose.prod.yml exec bill-docs-retry python scripts/retry_bill_documents.py
```

### Smoke tests post-despliegue

- [ ] `https://TU_DOMINIO` carga la SPA (rutas directas como `/login` funcionan)
- [ ] `https://TU_DOMINIO/health` devuelve `{"status":"healthy","database":"ok"}`
- [ ] Login y refresh de sesión
- [ ] Crear factura y verificar generación de PDF en el NAS
- [ ] Solo los puertos 80/443 están expuestos públicamente (el backend no publica `:8000`)
