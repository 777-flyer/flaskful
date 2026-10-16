# FlaskFul

**FlaskFul** is a scalable, security-hardened **RESTful API boilerplate** built with **Flask 3**, **Flask-Smorest (Marshmallow + OpenAPI 3)**, **SQLAlchemy 2.0**, **Flask-Migrate (Alembic)**, **Flask-JWT-Extended**, **Flask-Limiter**, **Flask-Caching**, and **Flask-CORS**.

Engineered as a standalone backend for decoupled frontends (React, Vue, Next.js, Mobile) with **OWASP API Security Top 10**, database hardening, caching, audit trails, and multi-platform deployment out of the box.

---

## Core Features

| Layer | Capabilities |
| :--- | :--- |
| **Architecture** | Application Factory (`create_app`), versioned blueprints (`/api/v1`), decoupled Service Layer, centralized extensions. |
| **Documentation** | Auto-generated **OpenAPI 3.0.3** spec with interactive **Swagger UI** (`/docs`) & **ReDoc** (`/redoc`) + JWT Bearer auth button. |
| **Authentication** | `scrypt:32768:8:1` password hashing, JWT access/refresh tokens, **single-use refresh token rotation**, and persistent JTI revocation (`token_blocklist`). |
| **API Security** | Rate limiting (`Flask-Limiter`), brute-force account lockout (`423 Locked`), timing-attack mitigation, RBAC (`@roles_required`), BOLA ownership checks, and `1 MB` payload limits. |
| **Audit & Logging** | Immutable `AuditLog` database trail (`user_id`, `action`, `ip_address`, `request_id`) + structured JSON logging (`LOG_FORMAT=json`). |
| **Data & Caching** | `Flask-Caching` (`SimpleCache` / `RedisCache`) with automatic per-user cache invalidation, `UUIDMixin` (public UUIDv4s), `SoftDeleteMixin` (`deleted_at` + restore), and dynamic sorting. |
| **Input Validation** | Strict Marshmallow `BaseSchema` (`unknown = RAISE` against mass-assignment), OWASP password policy, null-byte rejection, and SQL `ILIKE` wildcard escaping. |
| **HTTP & DB Hardening** | Automatic `CSP`, `HSTS`, `nosniff`, `DENY`, `Cache-Control: no-store`, `X-Request-ID`, `pool_pre_ping`, auto-rollback on error, and SQLite PRAGMAs (`foreign_keys=ON`, `trusted_schema=OFF`, `secure_delete=ON`, `WAL`). |
| **Deployment & CI** | Multi-stage non-root `Dockerfile`, `docker-compose.yml` (Postgres 16 + Redis 7 + Nginx), `gunicorn.conf.py`, `render.yaml`, `railway.json`, `Procfile`, and GitHub Actions CI. |

---

## Project Structure

```text
flaskful/
├── .github/workflows/ci.yml  # Automated Lint, Pytest & Docker build CI pipeline
├── app/
│   ├── api/v1/               # Blueprints: health.py, auth.py, items.py, admin.py
│   ├── core/                 # Security headers, RBAC, structured logging, exceptions, CLI
│   ├── models/               # SQLAlchemy 2.0: base.py, user.py, item.py, token_blocklist.py, audit_log.py
│   ├── schemas/              # Marshmallow schemas: common.py, auth.py, item.py, admin.py
│   ├── services/             # Business logic: auth_service.py, item_service.py, admin_service.py
│   ├── __init__.py           # Application Factory (create_app)
│   ├── config.py             # Environment configs (Dev, Test, Prod) + startup security validation
│   └── extensions.py         # db, migrate, api, jwt, cors, limiter, cache + SQLite PRAGMAs
├── deploy/nginx/nginx.conf   # Hardened Nginx reverse proxy config with edge rate limiting
├── docker/entrypoint.sh      # Container startup script
├── tests/                    # Pytest suite (auth, CRUD, soft-delete, RBAC admin, audit logs, security)
├── Dockerfile                # Multi-stage non-root production container image
├── docker-compose.yml        # Full production stack (API + PostgreSQL 16 + Redis 7 + Nginx)
├── gunicorn.conf.py          # Production Gunicorn WSGI server configuration
├── Procfile                  # Heroku / Dokku / PaaS process definition
├── railway.json              # Railway 1-click deployment config
├── render.yaml               # Render 1-click Blueprint (Web Service + Managed Postgres)
└── wsgi.py                   # WSGI entry point
```

---

## Quick Start (Local Development)

```powershell
# 1. Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment & initialize database
Copy-Item .env.example .env
flask init-db
flask seed-db   # Seeds demo@example.com (DemoPass123!) & admin@example.com (AdminPass123!)

# 4. Run development server
flask run
```

* **Swagger UI**: `http://localhost:5000/docs`
* **ReDoc**: `http://localhost:5000/redoc`
* **Health Check**: `http://localhost:5000/api/v1/health`

---

## Built-in Endpoints (`/api/v1`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | API status and database connectivity check |
| `POST` | `/api/v1/auth/register` | Public | Register user & issue access/refresh tokens |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user (with rate limit & lockout protection) |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT | Rotate single-use refresh token & issue new token pair |
| `POST` | `/api/v1/auth/logout` | Access/Refresh JWT | Revoke current token JTI in blocklist |
| `POST` | `/api/v1/auth/change-password` | Access JWT | Verify current password, update hash & revoke token |
| `GET` | `/api/v1/auth/me` | Access JWT | Retrieve current authenticated user profile |
| `GET` | `/api/v1/items` | Access JWT | Cached, paginated, filtered & sorted items (`?sort_by=title&sort_order=asc&include_deleted=false`) |
| `POST` | `/api/v1/items` | Access JWT | Create a new item (invalidates user cache) |
| `GET` | `/api/v1/items/<id>` | Access JWT | Get item by ID (enforces BOLA ownership) |
| `PATCH` | `/api/v1/items/<id>` | Access JWT | Partially update item by ID |
| `DELETE` | `/api/v1/items/<id>` | Access JWT | Soft-delete (archive) item by ID |
| `POST` | `/api/v1/items/<id>/restore` | Access JWT | Restore a soft-deleted item by ID |
| `GET` | `/api/v1/admin/users` | Admin JWT | List all users (protected by `@roles_required("admin")`) |
| `PATCH` | `/api/v1/admin/users/<id>` | Admin JWT | Update user role, active status, or unlock account |
| `GET` | `/api/v1/admin/audit-logs` | Admin JWT | Query security audit logs (`?action=USER_LOGIN_SUCCESS&user_id=1`) |

---

## Deployment Options

### 1. Docker & Docker Compose (PostgreSQL + Redis + Nginx)
```bash
docker compose up -d --build
```

### 2. Cloud PaaS (Render / Railway / Heroku)
* **Render**: Uses `render.yaml` Blueprint (Web Service + Managed PostgreSQL + auto-generated secrets).
* **Railway**: Uses `railway.json` (`Dockerfile` builder + `/api/v1/health` check).
* **Heroku / Dokku**: Uses `Procfile` (`web: gunicorn -c gunicorn.conf.py wsgi:app`).

### 3. VPS + Nginx Reverse Proxy
Run Gunicorn and use `deploy/nginx/nginx.conf` for edge rate limiting, `1M` request size enforcement, and proxy header forwarding (`TRUSTED_PROXY_COUNT=1`).

---

## Database Migrations & Testing

```powershell
# Alembic migrations (Flask-Migrate)
flask db init
flask db migrate -m "Initial schema"
flask db upgrade

# Run test suite (inside .venv)
.\.venv\Scripts\pytest -v
```
