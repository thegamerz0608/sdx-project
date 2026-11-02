# Containerized Deployment & Operations Guide (`docker-compose`)
**Project Title:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Documentation:** `docs/DOCKER.md`  
**Compose Version:** 3.8  
**Components:** MariaDB 10.11+ + FastAPI Uvicorn Web Server + Mailpit SMTP Testing Server  

---

## 1. Architectural Overview

The containerized stack provides a complete, self-contained development and staging environment for the **Faculty Attendance, Leave and Substitute Management ERP**. It eliminates manual database configuration and allows testing the entire multi-tier email notification workflow locally without exposing real SMTP credentials.

```
                              +---------------------------------------+
                              |         Host Browser / Client         |
                              +---------------------------------------+
                                  |              |               |
                    Port 8000     |              | Port 8025     | Port 3306
                    (Web & Kiosk) |              | (Mailpit UI)  | (MySQL client)
                                  v              v               v
           +-----------------------------+  +-------------+  +---------------+
           |    faculty_erp_web          |  |  mailpit    |  |  mariadb      |
           |  (FastAPI + Uvicorn)        |  | (SMTP Trap) |  | (MariaDB 10)  |
           +-----------------------------+  +-------------+  +---------------+
                          |                        ^                 ^
                          |       SMTP Port 1025   |                 |
                          +------------------------+                 |
                          |                                          |
                          +----------- DB Queries Port 3306 ---------+
```

---

## 2. Service Definitions

### 2.1 `mariadb` (Relational Database)
- **Base Image:** `mariadb:10.11`
- **Exposed Port:** `3306`
- **Volume Mounts:**
  - `mariadb_data`: Persistent named volume mounted at `/var/lib/mysql`.
  - `./database/schema.sql`: Mounted read-only into `/docker-entrypoint-initdb.d/01_schema.sql` to automatically seed tables and default roles upon initial startup.
- **Healthcheck:** Evaluates `healthcheck.sh --connect --innodb_initialized` every 10 seconds. Dependent services wait until MariaDB is fully initialized before booting.

### 2.2 `web` (FastAPI Application & Biometric Bridge)
- **Base Image:** Custom build via [`Dockerfile`](file:///d:/SNK(project)/Dockerfile) based on `python:3.11-slim`.
- **Exposed Port:** `8000`
- **Key Environment Variables:**
  - `DB_HOST=mariadb`, `DB_PORT=3306`
  - `SMTP_HOST=mailpit`, `SMTP_PORT=1025`
  - `SECRET_KEY`: Master cryptographic signing secret.
- **Volume Mounts:**
  - `./models`: Persists trained champion model and TF-IDF vectorizer weights.
  - `./backups`: Persists signed zip archives and encrypted snapshots.
  - `./logs`: Persists application execution and security audit logs.

### 2.3 `mailpit` (Zero-Config SMTP Mail Trapper)
- **Base Image:** `axllent/mailpit:latest`
- **SMTP Server Port:** `1025` (receives outgoing emails from the ERP approval chain).
- **Web UI Port:** `8025` (accessible in any web browser to view, inspect, and verify multi-tier HTML email formatting).
- **Features:** Accepts any sender credentials, displays HTML/plain-text tabs, and logs message headers without delivering to real external inboxes.

---

## 3. Quick Start Commands

### 3.1 Starting the Stack
```bash
# Build images and start all containers in detached mode
docker-compose up -d --build

# View real-time aggregated logs
docker-compose logs -f
```

### 3.2 Accessing Endpoints
| Service | Endpoint | Description |
|---|---|---|
| **Staff CMS Portal** | [http://localhost:8000/staff-login](http://localhost:8000/staff-login) | Faculty & HOD self-service portal |
| **Admin Gateway** | [http://localhost:8000/admin-login](http://localhost:8000/admin-login) | Isolated Administrator console |
| **Mobile Punch Client** | [http://localhost:8000/punch-interface](http://localhost:8000/punch-interface) | FIDO2 / WebAuthn biometric punch client |
| **Mailpit Web UI** | [http://localhost:8025](http://localhost:8025) | Trapped approval emails & notifications |
| **MariaDB Database** | `localhost:3306` | User: `faculty_app`, Password: `SecureDbPassword@2026!` |

### 3.3 Stopping the Stack
```bash
# Stop containers while preserving database volume
docker-compose down

# Stop and purge database volume (full reset)
docker-compose down -v
```

---

## 4. Production Hardening Notes

When deploying behind an enterprise reverse proxy (e.g. Nginx, Traefik, or Caddy):
1. **Enable HTTPS / TLS:** Configure an SSL certificate (Let's Encrypt / institutional certificate authority).
2. **Set Cookie Security:** Set `COOKIE_SECURE=true` in `.env` to enforce browser-level `Secure` cookie transmission.
3. **Pass Forwarded Headers:** Configure proxy to pass `X-Forwarded-For` and `X-Forwarded-Proto` so the rate limiter accurately records true client IP addresses.
