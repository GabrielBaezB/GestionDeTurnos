# ⚡ GestionDeTurnos — Sistema Inteligente de Gestión de Filas

Sistema completo de turnos y colas para atención al público, inspirado en ZeroQ. Construido con **FastAPI**, **PostgreSQL**, **Bootstrap 5** y **Server-Sent Events (SSE)** para actualizaciones en tiempo real.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Ejecución](#-instalación-y-ejecución)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Modelo de Datos](#-modelo-de-datos)
- [API Reference](#-api-reference)
- [Interfaces Frontend](#-interfaces-frontend)
- [Configuración](#-configuración)
- [Credenciales por Defecto](#-credenciales-por-defecto)

---

## ✨ Características

| Feature | Descripción |
|---------|-------------|
| **Multi-Trámite** | Múltiples tipos de atención (Ventas, Atención, Pagos, etc.) con prefijos independientes |
| **Numeración Independiente** | Cada trámite tiene su propia cola: V-001, A-001, P-001 |
| **Reset Diario** | Los contadores se reinician automáticamente cada día a las 00:00 |
| **Multi-Skill Routing** | Operadores asignados a uno o más trámites específicos |
| **SSE (Real-Time)** | Monitor y Clerk reciben actualizaciones instantáneas vía Server-Sent Events |
| **Autenticación JWT** | Login unificado para Admin y Operador con tokens OAuth2 |
| **Seguridad** | Passwords hasheados con `pbkdf2_sha256`, API no expone `hashed_password` |
| **Docker Ready** | Deploy con un solo comando: `docker-compose up -d` |
| **Responsive** | Bootstrap 5 dark theme, optimizado desde móvil hasta pantallas 4K |

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────┐
│                    Frontend                     │
│                                                 │
│  ┌──────┐ ┌──────┐ ┌───────┐ ┌─────┐ ┌───────┐  │
│  │Portal│ │Kiosco│ │Monitor│ │Clerk│ │ Admin │  │
│  └──┬───┘ └──┬───┘ └───┬───┘ └──┬──┘ └───┬───┘  │
│     │        │     SSE ↑│       │SSE     │      │
├─────┼────────┼─────────┼───────┼────────┼───────┤
│     └────────┴─────────┼───────┴────────┘       │
│                   FastAPI Backend               │
│                                                 │
│  ┌────────┐ ┌────────┐ ┌──────┐ ┌─────────────┐ │
│  │Tickets │ │Queues  │ │Login │ │  SSE Stream │ │
│  │  API   │ │  API   │ │ API  │ │  /stream    │ │
│  └────┬───┘ └────┬───┘ └──┬───┘ └──────┬──────┘ │
│       └──────────┴────────┴────────────┘        │
│                      SQLModel ORM               │
├─────────────────────────────────────────────────┤
│              PostgreSQL 16 (Docker)             │
│           ó SQLite (desarrollo local)           │
└─────────────────────────────────────────────────┘
```

---

## 📦 Requisitos Previos

- **Docker** + **Docker Compose** (recomendado)
- ó **Python 3.11+** para ejecución local

---

## 🚀 Instalación y Ejecución

### Opción 1: Docker (Recomendado)

```bash
# Clonar el proyecto
git clone <repositorio> && cd ZeroQrobo

# Levantar servicios (PostgreSQL + Backend)
docker-compose up -d --build

# Ver logs
docker-compose logs -f backend
```

La aplicación estará disponible en **http://localhost:8000**

### Opción 2: Local (Desarrollo)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar (usa SQLite por defecto)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Nota:** En modo local se usa SQLite (`backend/app.db`). En Docker se usa PostgreSQL automáticamente.

---

## 📁 Estructura del Proyecto

```
ZeroQrobo/
├── docker-compose.yml          # Orquestación: PostgreSQL + Backend
├── Dockerfile                  # Imagen Python 3.11-slim
├── requirements.txt            # Dependencias Python
├── .env                        # Variables de entorno (local)
│
├── backend/
│   └── app/
│       ├── main.py             # App FastAPI, lifespan, rutas estáticas
│       ├── init_auth.py        # Seed: admin, operador, módulo, trámites
│       │
│       ├── api/
│       │   ├── deps.py         # Dependencias (sesión DB, auth)
│       │   └── v1/
│       │       ├── api.py      # Router principal
│       │       └── endpoints/
│       │           ├── login.py      # Auth JWT (admin + operador)
│       │           ├── tickets.py    # CRUD tickets + SSE stream
│       │           ├── queues.py     # CRUD trámites
│       │           ├── modules.py    # CRUD módulos
│       │           ├── operators.py  # CRUD operadores + queue assignment
│       │           └── users.py      # CRUD usuarios admin
│       │
│       ├── core/
│       │   ├── config.py       # Settings (Pydantic BaseSettings)
│       │   ├── database.py     # Engine SQLModel + sesión
│       │   ├── events.py       # SSE EventManager (asyncio Queue)
│       │   └── security.py     # Hash passwords, JWT tokens
│       │
│       ├── models/
│       │   ├── ticket.py       # Modelo Ticket + estados
│       │   ├── queue.py        # Modelo Queue (trámites)
│       │   ├── operator.py     # Modelo Operator + schemas
│       │   ├── operator_queue.py # M2M Operator ↔ Queue
│       │   ├── module.py       # Modelo Module (mesones)
│       │   └── user.py         # Modelo User (admin)
│       │
│       └── crud/               # Operaciones CRUD genéricas
│
└── frontend/
    ├── index.html              # Portal principal
    ├── kiosk.html              # Kiosco: emisión de tickets
    ├── monitor.html            # Monitor TV: pantalla pública
    ├── clerk.html              # Operador: panel de atención
    ├── admin.html              # Admin: configuración del sistema
    └── style.css               # Sistema de diseño premium
```

---

## 🗄 Modelo de Datos

```mermaid
erDiagram
    Queue ||--o{ Ticket : "genera"
    Queue ||--o{ OperatorQueue : "asignada a"
    Operator ||--o{ OperatorQueue : "atiende"
    Operator ||--o{ Ticket : "sirve"
    Module ||--o{ Operator : "asignado"

    Queue {
        int id PK
        string name
        string prefix
        bool is_active
    }

    Ticket {
        int id PK
        string number
        string queue_type
        int queue_id FK
        enum status "waiting|serving|completed"
        string phone_number
        int served_by_module_id
        int served_by_operator_id FK
        datetime created_at
        datetime updated_at
    }

    Operator {
        int id PK
        string name
        string username
        string hashed_password
        bool is_active
        int current_module_id FK
        datetime created_at
        datetime updated_at
    }

    OperatorQueue {
        int id PK
        int operator_id FK
        int queue_id FK
    }

    Module {
        int id PK
        string name
        bool is_active
    }
```

### Flujo de Numeración

Cada trámite tiene su **cola independiente** con numeración que **se reinicia diariamente**:

```
Cola "Ventas" (prefix V):    V-001, V-002, V-003, ...
Cola "Atención" (prefix A):  A-001, A-002, A-003, ...
Cola "Pagos" (prefix P):     P-001, P-002, ...
```

Al día siguiente, todas las colas reinician en `001`.

---

## 🔌 API Reference

Base URL: `/api/v1`

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/login/access-token` | Login OAuth2 (admin o operador) |

**Body** (form-urlencoded):
```
username=admin@zeroq.cl&password=admin
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "role": "admin",
  "name": "admin@zeroq.cl",
  "id": 1
}
```

---

### Tickets

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/tickets/` | Crear ticket (desde kiosco) |
| `POST` | `/tickets/call-next` | Llamar siguiente ticket (desde clerk) |
| `GET` | `/tickets/monitor` | Datos del monitor (REST fallback) |
| `GET` | `/tickets/stream` | **SSE** — stream de eventos en tiempo real |
| `POST` | `/tickets/{id}/complete` | Marcar ticket como completado |
| `POST` | `/tickets/{id}/recall` | Re-llamar un ticket |
| `GET` | `/tickets/active-sessions` | Sesiones activas |
| `POST` | `/tickets/reset-queue` | Resetear cola de espera |

**Crear ticket:**
```json
POST /tickets/
{ "queue_id": 1 }
→ { "id": 5, "number": "V-003", "status": "waiting", ... }
```

**Llamar siguiente:**
```json
POST /tickets/call-next
{ "operator_id": 1, "module_id": 1, "queue_ids": [1, 2] }
→ { "id": 5, "number": "V-003", "status": "serving", ... }
```

**SSE Stream:**
```
GET /tickets/stream
→ data: {"type":"ticket_called","data":{"serving":[...],"waiting":[...],"event":{"number":"V-003","module_id":1}}}
```

---

### Trámites (Queues)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/queues/` | Listar trámites |
| `POST` | `/queues/` | Crear trámite |
| `PUT` | `/queues/{id}` | Actualizar trámite |
| `DELETE` | `/queues/{id}` | Eliminar trámite |

**Crear trámite:**
```json
POST /queues/
{ "name": "Ventas", "prefix": "V", "is_active": true }
```

---

### Módulos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/modules/` | Listar módulos |
| `POST` | `/modules/` | Crear módulo |
| `PUT` | `/modules/{id}` | Actualizar módulo |
| `DELETE` | `/modules/{id}` | Eliminar módulo |

---

### Operadores

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/operators/` | Listar operadores | ✅ |
| `GET` | `/operators/{id}` | Detalle (incluye `queue_ids`) | ✅ |
| `POST` | `/operators/` | Crear operador + asignar trámites | ✅ |
| `PUT` | `/operators/{id}` | Actualizar operador | ✅ |
| `DELETE` | `/operators/{id}` | Eliminar operador | ✅ |

**Crear operador con trámites:**
```json
POST /operators/
{
  "name": "Juan Pérez",
  "username": "juan",
  "password": "1234",
  "is_active": true,
  "queue_ids": [1, 2]
}
```

---

## 🖥 Interfaces Frontend

| Ruta | Interfaz | Propósito |
|------|----------|-----------|
| `/` | **Portal** | Página principal con accesos directos |
| `/kiosk` | **Kiosco** | Pantalla táctil/pública para emitir tickets |
| `/monitor` | **Monitor** | Pantalla TV que muestra turnos en tiempo real (SSE) |
| `/clerk` | **Operador** | Panel de atención: login, selección de módulo/trámites, llamar/completar tickets |
| `/admin` | **Admin** | Gestión del sistema: módulos, trámites, operadores |

### Stack Frontend
- **Bootstrap 5.3.3** (CDN) + **Bootstrap Icons**
- **Google Fonts** (Outfit)
- **Dark Theme** (`data-bs-theme="dark"`)
- **SSE** (`EventSource`) para monitor y clerk

---

## ⚙ Configuración

### Variables de Entorno (`.env`)

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `DATABASE_URL` | Conexión a base de datos | `sqlite:///./backend/app.db` |
| `SECRET_KEY` | Clave para firmar JWT | `super_secret_real` |

> ⚠️ **Producción:** Cambiar `SECRET_KEY` por una clave segura y `DATABASE_URL` por PostgreSQL.

### Docker Compose Override

En Docker, `DATABASE_URL` se sobreescribe a:
```
postgresql://postgres:password@postgres:5432/zeroqrobo
```

### Parámetros de la App (`core/config.py`)

| Parámetro | Valor |
|-----------|-------|
| `ALGORITHM` | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 |
| `BACKEND_CORS_ORIGINS` | localhost:8000, localhost:3000 |

---

## 🔑 Credenciales por Defecto

| Rol | Usuario | Contraseña | Interfaz |
|-----|---------|------------|----------|
| **Admin** | `admin@zeroq.cl` | `admin` | `/admin` |
| **Operador** | `operador` | `1234` | `/clerk` |

> Estos usuarios se crean automáticamente al iniciar la aplicación por primera vez (`init_auth.py`).

---

## 🐳 Docker

### Servicios

| Servicio | Imagen | Puerto | Healthcheck |
|----------|--------|--------|-------------|
| `postgres` | `postgres:16` | 5432 | `pg_isready` cada 5s |
| `backend` | Build local | 8000 | — |

### Comandos Útiles

```bash
# Levantar todo
docker-compose up -d --build

# Solo reconstruir backend
docker-compose up -d --build backend

# Ver logs en tiempo real
docker-compose logs -f backend

# Detener todo
docker-compose down

# Detener y eliminar datos
docker-compose down -v
```

---

## 📄 Licencia

Proyecto desarrollado para gestión de filas y turnos. Uso interno.


