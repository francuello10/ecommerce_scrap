# Competitive Intelligence Engine — Project Documentation

> **Para AIs (Cursor, Antigravity, Copilot, etc.) y humanos.**
> Este archivo es el punto de entrada único para entender el proyecto.
> Léelo completo antes de tocar cualquier archivo.

---

## 🎯 ¿Qué hace este proyecto?

Motor de **inteligencia competitiva para eCommerce**. Monitorea sitios web y newsletters de competidores, detecta cambios (nuevas promos, financiación, tech stack), y genera **briefs diarios** con alertas en Slack.

**Stack:** Python 3.12 · FastAPI · PostgreSQL 16 · Directus 11 · ARQ (Redis) · SQLAlchemy 2.0 · HTTPX · Playwright · imap-tools

---

## 📁 Estructura del Proyecto

```
ecommerce_scrap/
├── src/
│   ├── core/
│   │   ├── config.py          # Settings (pydantic-settings). Lee el .env.
│   │   ├── database.py        # Engine async SQLAlchemy + Base + get_db()
│   │   ├── models.py          # TODOS los modelos ORM (23 tablas)
│   │   └── notifications/
│   │       └── slack.py       # Sender de alertas Slack (httpx async)
│   ├── api/
│   │   └── main.py            # FastAPI app. Entry point: uvicorn src.api.main:app
│   └── workers/
│       └── web_monitor/       # Web scraping engine
│           ├── models.py      # Dataclasses: ExtractionResult, PromoSignal, etc.
│           ├── platform_detector.py  # Layer 1: heurísticas por regex (VTEX, Shopify...)
│           ├── extractor_factory.py  # Router: instancia el extractor correcto
│           └── extractors/
│               ├── base.py          # BaseExtractor (abstract)
│               ├── vtex.py          # VTEX IO extractor stub
│               ├── shopify.py       # Shopify extractor stub
│               ├── generic_html.py  # Fallback (BS4)
│               └── ...             # magento, tiendanube, woocommerce, prestashop
├── alembic/                   # Migraciones de DB
│   ├── env.py                 # Config de Alembic (usa PYTHONPATH=src)
│   └── versions/              # Archivos de migración generados
├── scripts/
│   ├── seed_tiers.py          # Inserta BASIC/PROFESSIONAL/ENTERPRISE en DB
│   └── _test_*.py             # Scripts de prueba temporales (se borran)
├── docs/                      # Documentación arquitectónica (ver abajo)
├── tests/                     # Tests unitarios e integración
├── docker-compose.yml         # Postgres 5433 + Redis 6379 + Directus 8055
├── .env                       # Variables de entorno (NO commitear)
├── .env.example               # Template del .env (sí commitear)
├── pyproject.toml             # Dependencias (uv)
└── Makefile                   # Shortcuts: make up, make db-upgrade, etc.
```

---

## ⚡ Setup Rápido (Primera vez)

```bash
# 1. Clonar y entrar al directorio
cd ecommerce_scrap

# 2. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales

# 3. Instalar dependencias
make install

# 4. Levantar infraestructura (Postgres, Redis, Directus)
make up

# 5. Aplicar migraciones
make db-upgrade

# 6. Insertar planes de suscripción
make db-seed

# 7. Levantar la API
make api
```

**Puertos locales:**
| Servicio | Puerto |
|:---|:---|
| FastAPI | http://localhost:8000 |
| Directus | http://localhost:8055 |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |

**Directus login:** `admin@intel.local` / `admin_dev_2026`

---

## 🗺️ Documentación Arquitectónica (`docs/`)

| Archivo | Contenido |
|:---|:---|
| `01_architecture.md` | Stack, principios de diseño |
| `02_database_schema.md` | Modelo de datos completo (23 tablas) |
| `03_workflows.md` | Flujos de los 6 workers/crons |
| `04_legacy_rescue_plan.md` | Lo que se rescató del proyecto Go legacy |
| `05_stack_versions.md` | Versiones exactas de todas las librerías |
| `06_product_vision_cmo.md` | Visión de producto / CMO |
| `07_tech_fingerprinting.md` | Estrategia de detección de stack tecnológico |
| `08_pluggable_extractors.md` | Strategy Pattern para extractors por plataforma |
| `09_operational_flow.md` | Flujo completo: onboarding → brief diario |
| `10_saas_business_model.md` | Multi-tenant, feature flags, upsell flow |

---

## 🗄️ Base de Datos — Tablas Clave

### SaaS / Multi-Tenant
- `subscription_tier` — Planes: BASIC ($49), PROFESSIONAL ($149), ENTERPRISE ($499). **Editables desde Directus.**
- `client` — Agencias/marcas clientes. Vinculadas a un tier.
- `client_competitor` — N:N entre client y competitor. `is_baseline=True` = "esta es MI empresa". `history_access_start_date` = llave del upsell histórico.

### Configuración (editables en Directus)
- `competitor` — **Global**. No pertenece a ningún cliente. `domain` es UNIQUE.
- `monitored_page` — URLs a monitorear por competidor. Auto-descubiertas del header/footer.
- `newsletter_account` — Casilla IMAP de monitoreo (`newsbriefai.dev@gmail.com`).
- `newsletter_subscription` — Estado de suscripción al newsletter de cada competidor.

### Operativas (solo lectura en Directus)
- `page_snapshot` — HTML crudo capturado. Append-only.
- `detected_signal` — Señal extraída (promo, cuota, envío gratis, CTA).
- `change_event` — Cambio detectado entre dos snapshots. Si `severity=CRITICAL` → alerta Slack.
- `daily_brief` / `weekly_brief` — Briefs generados.

### Tech Fingerprinting
- `competitor_tech_profile` — Stack actual del competidor (1:1). `is_valid=False` → recalibrar.
- `tech_profile_history` — Historial de cambios de stack (1:N, append-only).

---

## 🤖 Workers / Jobs Principales

| Worker | Trigger | Feature Flag |
|:---|:---|:---|
| `competitor_onboarding` | Al crear competidor | Siempre |
| `web_monitor` | Cron (1x/3x/6x día según tier) | Siempre |
| `newsletter_monitor` (IMAP) | Cron cada 15 min | `can_track_newsletters` |
| `tech_fingerprint` | Cron semanal (domingos 3AM) | `can_track_tech_stack` |
| `diff_engine` | Cascada post-scraping | Siempre |
| `briefing` | Cron diario 8:30AM | Siempre |

**Regla clave:** El orquestador **verifica los feature flags del tier del cliente antes de encolar** tareas costosas (Playwright, wappalyzer). Sin el flag → no se encola.

---

## 🔑 Variables de Entorno Importantes

```bash
DATABASE_URL=postgresql+asyncpg://intel:intel_dev_2026@localhost:5433/competitive_intel
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=...          # Para generar briefs con IA
EMAIL_SERVER_USER=newsbriefai.dev@gmail.com
EMAIL_SERVER_PASSWORD=...   # Gmail App Password
SLACK_WEBHOOK_URL=...       # Para alertas en tiempo real
```

---

## 🛠️ Comandos Make

```bash
make help          # Ver todos los comandos disponibles
make up            # Levantar Docker (Postgres + Redis + Directus)
make down          # Apagar Docker
make install       # Instalar dependencias con uv
make api           # Levantar FastAPI (dev mode con hot-reload)
make worker        # Levantar ARQ worker
make db-upgrade    # Aplicar migraciones
make db-migrate    # Crear nueva migración (pide descripción)
make db-seed       # Insertar planes de suscripción iniciales
make test          # Correr tests
make lint          # Chequear código con Ruff
make format        # Formatear código
```

---

## 🏗️ Guía para Agregar Código Nuevo

### Agregar un nuevo worker
1. Crear `src/workers/<nombre>/worker.py`
2. Definir la función async como job ARQ
3. Registrarlo en `src/workers/worker_settings.py`
4. Agregar el feature flag correspondiente en `SubscriptionTier`

### Agregar un nuevo extractor de plataforma
1. Crear `src/workers/web_monitor/extractors/<plataforma>.py`
2. Heredar de `BaseExtractor`
3. Implementar los métodos abstractos
4. Registrarlo en `ExtractorFactory.__platform_map`
5. Agregar la heurística en `PlatformDetector`

### Agregar una nueva tabla
1. Definir el modelo en `src/core/models.py`
2. `make db-migrate` (pide descripción)
3. `make db-upgrade`
4. Directus auto-introspección verá la nueva tabla

---

## 📮 Convenciones de Código

- **Tipado estricto:** Todo con type hints. Usar `from __future__ import annotations`.
- **Async everywhere:** Funciones de DB y HTTP siempre async.
- **ORM solo para queries simples.** Queries complejas → `select()` con SQLAlchemy Core.
- **Sin lógica en modelos.** Los modelos son DTOs. La lógica va en servicios/workers.
- **Fail-fast en config:** Si falta una variable de entorno requerida, el sistema falla al iniciar.
- **Formatter:** Ruff (`make format`). Line length: 100.
