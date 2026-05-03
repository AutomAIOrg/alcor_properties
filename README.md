<<<<<<< HEAD
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
└── frontend_angular/         # SPA Angular
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

### 2. Migración de base de datos

Si la tabla `bookings` no tiene todavía la columna de notas, ejecuta:

```sql
ALTER TABLE bookings ADD COLUMN Notes TEXT NULL;
```

---

## Instalación y arranque

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

La API queda disponible en `http://localhost:8000`.  
Documentación interactiva: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend_angular
npm install
ng serve
```

La aplicación queda disponible en `http://localhost:4200`.  
Las peticiones a `/api/*` se redirigen automáticamente al backend mediante el proxy configurado en `proxy.conf.json`.

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
- **Filtros múltiples** por piso (`booking_id`) y estado, con checkboxes desplegables
- **Modal de detalle y edición** de reservas existentes
- **Modal de creación** de nuevas reservas con validación, cálculo automático de noches y selector de piso desde la base de datos
- **Estados de reserva**: `Confirmed`, `Pending`, `Cancelled`, `ok` (configurables en `booking.model.ts`)
- Diseño **responsive** con soporte móvil
=======
# alcor_properties
App web para la gestión de alquileres y limpiezas de pisos
>>>>>>> 744558a6ca6c400d11940ff2d63ebb47145f86b3
