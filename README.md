<div align="center">

# 🔍 Competitive Intelligence Engine

**Motor de inteligencia competitiva para eCommerce.**
Monitorea competidores, detecta cambios en tiempo real, y genera briefs accionables.

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-316192.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ Features

### 🎯 Competitor Suggestion Engine *(NEW)*
> Al registrar tu empresa, el sistema sugiere competidores automáticamente basado en tu industria, segmentados en 3 niveles de alcance:

| Nivel | Descripción | Ejemplo (Deportes AR) |
|:---|:---|:---|
| 🌍 **Global Benchmark** | Referentes mundiales del rubro | Nike.com, Adidas.com |
| 🌎 **Regional Rival** | Competidores LATAM/regionales | Dafiti, Netshoes |
| 🏠 **Direct Rival** | Competencia directa nacional/local | Newsport, Dexter, Moov |

### 🕷️ Web Monitoring
- **Platform-aware scraping**: Detección automática de VTEX, Shopify, Magento, TiendaNube, WooCommerce, PrestaShop
- **Signal extraction**: Promociones (% OFF, 2x1), financiación (cuotas sin interés), CTAs, hero banners
- **Auto-discovery**: Escaneo de header/footer para descubrir páginas clave (promos, financiación, envíos)
- **Dual capture**: Screenshots con y sin popups + HTML para análisis full-context
- **Full-page scroll**: Captura below-the-fold para no perder promos ocultas

### 📧 Newsletter Intelligence
- **Auto-subscription**: Suscripción automática a newsletters de competidores via Playwright
- **Double opt-in handler**: Confirmación automática de emails de verificación via IMAP
- **Visual + HTML analysis**: Renderizado de imagen para LLM + HTML para datos duros
- **Frequency analysis**: "Tu competidor envía ofertas los martes a las 10 AM"

### 🔔 Real-Time Alerts
- **Diff engine**: Detección automática de cambios entre snapshots
- **Slack alerts**: Notificación inmediata cuando un competidor lanza una promo nueva o cambia precios
- **Severity levels**: LOW → MEDIUM → HIGH → CRITICAL (solo CRITICAL dispara alerta inmediata)

### 📊 Daily Briefs
- **Brief diario**: Resumen ejecutivo de todas las actividades competitivas en 24h
- **Brief semanal**: Tendencias y patrones a lo largo de la semana
- **Baseline comparison**: "Us vs. Them" — compará tu empresa contra cada competidor

### 🔬 Tech Stack Fingerprinting
- **Layer 1**: Heurísticas rápidas (regex en HTML + headers HTTP)
- **Layer 2**: Deep fingerprinting con wappalyzer (analytics, payments, CDN, JS frameworks)
- **Change tracking**: Alertas cuando un competidor cambia de plataforma o agrega herramientas

### 💰 SaaS Multi-Tenant
- **3 planes**: BASIC ($49), PROFESSIONAL ($149), ENTERPRISE ($499) — editables desde Directus
- **Feature flags**: Cada feature está gated por el tier del cliente
- **Upsell engine**: Cuando un cliente agrega un competidor que ya existe → se le ofrece desbloquear el historial

---

## 🚀 Quick Start

```bash
# 1. Clonar el repositorio
git clone https://github.com/francuello10/ecommerce_scrap.git
cd ecommerce_scrap

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Instalar dependencias
make install

# 4. Levantar infraestructura
make up

# 5. Aplicar migraciones + seed data
make db-upgrade
make db-seed
make db-seed-data

# 6. Levantar la API
make api
```

| Servicio | URL |
|:---|:---|
| FastAPI (API) | http://localhost:8000 |
| Directus (Admin) | http://localhost:8055 |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        DIRECTUS 11                               │
│                    (Admin Panel / CMS)                            │
│     Manages: Competitors, Tiers, Feature Flags, Industries       │
└───────────────────────┬──────────────────────────────────────────┘
                        │ reads schema
┌───────────────────────┼──────────────────────────────────────────┐
│                  POSTGRESQL 16                                    │
│   23+ tables: SaaS tenancy, competitors, snapshots, signals...   │
└───────────────────────┬──────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
   │ FastAPI  │    │ ARQ Worker│   │ ARQ Worker│
   │  API     │    │ Web Mon.  │   │ Newsletter│
   │ :8000    │    │ (HTTPX/PW)│   │ (IMAP)    │
   └──────────┘    └───────────┘   └───────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
                   ┌────▼────┐
                   │  Redis  │
                   │  7.2    │
                   │ (Broker)│
                   └─────────┘
```

---

## 📁 Project Structure

```
ecommerce_scrap/
├── src/
│   ├── core/
│   │   ├── config.py              # pydantic-settings (fail-fast)
│   │   ├── database.py            # Async SQLAlchemy 2.0 engine
│   │   ├── models.py              # ALL ORM models (25+ tables)
│   │   └── notifications/
│   │       └── slack.py           # Async Slack webhook
│   ├── api/
│   │   └── main.py                # FastAPI app + /health
│   └── workers/
│       └── web_monitor/
│           ├── orchestrator.py    # Main ARQ job
│           ├── discovery.py       # Header/footer auto-discovery
│           ├── platform_detector.py  # Layer 1 heuristics
│           ├── extractor_factory.py  # Strategy Pattern router
│           └── extractors/        # 7 platform extractors
├── alembic/                       # DB migrations
├── scripts/                       # Seed scripts
├── docs/                          # 10 architecture documents
├── docker-compose.yml             # Postgres + Redis + Directus
├── Makefile                       # 20+ commands (make help)
├── CLAUDE.md                      # AI-friendly project docs
└── pyproject.toml                 # Dependencies (uv)
```

---

## 🛠️ Make Commands

```bash
make help           # 📋 Ver todos los comandos disponibles
make up             # 🟢 Levantar Docker (Postgres + Redis + Directus)
make down           # 🔴 Apagar Docker
make install        # 📦 Instalar dependencias con uv
make api            # 🌐 Levantar FastAPI (dev mode)
make worker         # ⚙️  Levantar ARQ worker
make db-upgrade     # ⬆️  Aplicar migraciones
make db-migrate     # 🗄️  Nueva migración (pide descripción)
make db-seed        # 🌱 Insertar planes de suscripción
make db-seed-data   # 📧 Insertar datos iniciales
make test           # 🧪 Correr tests
make lint           # 🔍 Chequear código con Ruff
make format         # ✨ Formatear código
```

---

## 🗄️ Database Schema

### Core Tables (25+)

| Grupo | Tablas | Descripción |
|:---|:---|:---|
| **SaaS** | `subscription_tier`, `client`, `client_competitor`, `upsell_event` | Multi-tenant con feature flags |
| **Suggestions** | `industry`, `competitor_industry` | Suggestion Engine por rubro y nivel |
| **Config** | `competitor`, `monitored_page`, `newsletter_account`, `newsletter_subscription`, `signal_taxonomy` | Configuración editable desde Directus |
| **Raw** | `crawl_run`, `page_snapshot`, `newsletter_message`, `job_execution_log` | Datos crudos (append-only) |
| **Tech** | `competitor_tech_profile`, `tech_profile_history`, `tech_profile_change` | Fingerprinting tecnológico |
| **Catalog** | `product`, `price_history` | Preparado para Fase 2 |
| **Results** | `detected_signal`, `change_event` | Señales y eventos de cambio |
| **Briefs** | `daily_brief`, `weekly_brief` | Reportes generados |

---

## 🧠 Tech Stack

| Component | Technology |
|:---|:---|
| Language | Python 3.12+ |
| API Framework | FastAPI 0.115+ |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Worker Queue | ARQ (Redis) |
| Admin Panel | Directus 11 |
| HTTP Client | HTTPX |
| Browser Automation | Playwright |
| Email | imap-tools |
| AI/LLM | Gemini 1.5 Flash |
| Package Manager | uv (Astral) |
| Task Runner | GNU Make |
| Linter/Formatter | Ruff |

---

## 📚 Documentation

Toda la documentación vive en [`docs/`](docs/):

| Doc | Contenido |
|:---|:---|
| [01_architecture.md](docs/01_architecture.md) | Stack + principios de diseño |
| [02_database_schema.md](docs/02_database_schema.md) | Modelo de datos completo |
| [03_workflows.md](docs/03_workflows.md) | Flujos de workers/crons |
| [05_stack_versions.md](docs/05_stack_versions.md) | Versiones exactas de todo |
| [07_tech_fingerprinting.md](docs/07_tech_fingerprinting.md) | Detección de tech stack |
| [08_pluggable_extractors.md](docs/08_pluggable_extractors.md) | Strategy Pattern para extractors |
| [09_operational_flow.md](docs/09_operational_flow.md) | Flujo completo onboarding → brief |
| [10_saas_business_model.md](docs/10_saas_business_model.md) | Multi-tenant + upsell |

Para AI assistants (Cursor, Copilot, etc.), ver [`CLAUDE.md`](CLAUDE.md).

---

## 🗺️ Roadmap

### ✅ Implementado
- [x] Infrastructure (Docker, Postgres, Redis, Directus)
- [x] 25+ SQLAlchemy models con migraciones
- [x] Web Monitor: platform detection, signal extraction, auto-discovery
- [x] Suggestion Engine: industry-based competitor recommendations (3 levels)
- [x] SaaS multi-tenant con feature flags editables

### 🔜 Próximas Fases
- [ ] **Newsletter Monitor**: IMAP reader + auto-subscription + double opt-in handler
- [ ] **Diff Engine + Alertas Slack**: Detección de cambios entre snapshots + alertas CRITICAL
- [ ] **Briefing Engine**: Daily/weekly briefs con baseline comparison

### 🔮 Fases Futuras
- [ ] **📦 Catalog Scraping** — Scraping completo del catálogo de productos de cada competidor. Tracking de precios, stock, productos nuevos/retirados. Usa las tablas `product` + `price_history` (ya creadas).
- [ ] **👁️ Vision LLM Analysis** — Capturas de pantalla duales (con/sin popups) + full-page scroll. El LLM analiza la propuesta visual (hero banners, jerarquía de precios, CTAs). Usa Playwright para screenshots + Gemini Vision para análisis.
- [ ] **📧 Newsletter Visual Analysis** — Renderizado de newsletters a imagen para análisis LLM. Métricas de frecuencia de envío por competidor.
- [ ] **📊 Dashboard Frontend** — Panel web con gráficos de evolución de señales, comparativas entre competidores, y alertas en tiempo real.
- [ ] **🔌 API Pública** — REST API para integraciones externas (gated por tier ENTERPRISE).

---

## 🤝 Contributing

```bash
# Setup dev environment
make install
make up
make db-upgrade

# Before pushing
make lint
make format
make test
```

---

## 📄 License

MIT © 2026 Francisco Cuello
