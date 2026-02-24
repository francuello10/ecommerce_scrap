<div align="center">

# 🔍 Competitive Intelligence Engine
### The Strategic Edge for Modern eCommerce

**Motor de inteligencia competitiva de grado enterprise.**
Transformamos el caos del monitoreo web y newsletters en señales de negocio accionables, alertas en tiempo real y briefings estratégicos impulsados por IA.

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-316192.svg)](https://www.postgresql.org/)
[![AI-Powered](https://img.shields.io/badge/AI-Briefing_Engine-purple.svg)]()

</div>

---

## 📈 Business Vision
En un mercado de eCommerce saturado, la velocidad de reacción es el mayor activo competitivo. Este engine permite a los CMOs y Gerentes de eCommerce:
- **Time-to-React < 1h**: Detectar cambios agresivos en la competencia (promos flash, cambios de envío) antes de que impacten en tu conversión.
- **Shadow Pricing Tracking**: Entender no solo el precio de lista, sino la agresividad real de las cuotas y promociones bancarias.
- **Strategic Briefing**: Eliminar el ruido operativo con resúmenes ejecutivos diarios generados por IA, listos para la toma de decisiones.

---

## ✨ Features

### 🎯 Competitor Suggestion Engine *(NEW)*
> Al registrar tu empresa, el sistema sugiere competidores automáticamente basado en tu industria, segmentados en 3 niveles de alcance:

| Nivel | Descripción | Ejemplo (Deportes AR) |
|:---|:---|:---|
| 🌍 **Global Benchmark** | Referentes mundiales del rubro | Nike.com, Adidas.com |
| 🌎 **Regional Rival** | Competidores LATAM/regionales | Dafiti, Netshoes |
| 🏠 **Direct Rival** | Competencia directa nacional/local | Newsport, Dexter, Moov |

### 🕷️ Web Monitoring (Powered by Scrapling 0.4)
- **High-Performance Parsing**: Motor de crawling ultrarrápido con **Scrapling**, reduciendo el overhead de procesamiento en un 40%.
- **Platform-aware scraping**: Detección automática y extractores nativos para VTEX IO, Shopify, Magento 2, TiendaNube, WooCommerce, PrestaShop y Salesforce Commerce Cloud (SFCC).
- **Signal extraction**: Promociones (% OFF, 2x1, combos), financiación (cuotas sin interés, bancos), CTAs, hero banners.
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

### 📊 AI Intelligence Briefs
- **Customizable AI Briefing**: Los reportes no son estáticos. Podes editar el **System Prompt** desde Directus para cambiar el tono, foco o idioma de los reportes generados por IA.
- **Daily Brief**: Resumen ejecutivo de todas las actividades competitivas en 24h generado por LLM (Gemini/GPT).
- **Weekly Brief**: Tendencias y patrones a lo largo de la semana.
- **Baseline comparison**: "Us vs. Them" — compará tu empresa contra cada competidor.

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
make db-setup-all
PYTHONPATH=src uv run python scripts/seed_ai_settings.py

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
│     Manages: Competitors, Tiers, AI Prompts, Industries          │
└───────────────────────┬──────────────────────────────────────────┘
                        │ reads schema
┌───────────────────────┼──────────────────────────────────────────┐
│                  POSTGRESQL 16                                    │
│   25+ tables: SaaS tenancy, AI Settings, Snapshots, Catalog...   │
└───────────────────────┬──────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
   │ FastAPI  │    │ ARQ Worker│   │ ARQ Worker│
   │  API     │    │ Monitoring│   │ AI Brief. │
   │ :8000    │    │ (HTTPX/PW)│   │ (LLM API) │
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
│   │       └── slack.py           # Async Slack webhook (Future)
│   ├── api/
│   │   └── main.py                # FastAPI app + /health
│   └── workers/
│       ├── briefing/
│       │   └── generator.py       # AI Briefing Engine (Custom Prompts)
│       └── web_monitor/
│           ├── orchestrator.py    # Main ARQ job
│           ├── discovery.py       # Header/footer auto-discovery
│           └── extractors/        # 7 platform extractors + Catalog
├── alembic/                       # DB migrations
├── scripts/                       # Seed scripts (Tiers, AI, Industries)
├── docs/                          # 10 architecture documents
├── Makefile                       # 20+ commands (make help)
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
make db-setup-all   # 🚀 Setup completo (Tiers, Data, Industries)
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
| **AI Briefing** | `ai_generator_settings`, `daily_brief`, `weekly_brief` | Prompts personalizables y reportes |
| **Suggestions** | `industry`, `competitor_industry` | Suggestion Engine por rubro y nivel |
| **Config** | `competitor`, `monitored_page`, `newsletter_account`, `newsletter_subscription` | Configuración editable desde Directus |
| **Raw Data** | `page_snapshot`, `newsletter_message`, `job_execution_log` | Datos crudos para análisis |
| **Tech** | `competitor_tech_profile`, `tech_profile_history`, `tech_profile_change` | Fingerprinting tecnológico |
| **Catalog** | `product`, `price_history` | Tracking de SKU, Precios y Stock |
| **Signals** | `detected_signal`, `change_event` | Hallazgos comerciales detectados |

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
| AI / LLM | Gemini 1.5 Pro / Flash |
| Parsing Engine | Scrapling (Turbo Selector) |
| Package Manager | uv (Astral) |

---

## 📚 Documentation

Toda la documentación vive en [`docs/`](docs/):

| Doc | Contenido |
|:---|:---|
| [01_architecture.md](docs/01_architecture.md) | Stack + principios de diseño |
| [02_database_schema.md](docs/02_database_schema.md) | Modelo de datos completo |
| [03_workflows.md](docs/03_workflows.md) | Flujos de workers/crons |
| [08_pluggable_extractors.md](docs/08_pluggable_extractors.md) | Strategy Pattern para extractors |
| [10_saas_business_model.md](docs/10_saas_business_model.md) | Multi-tenant + upsell |

Para AI assistants (Cursor, Copilot, etc.), ver [`CLAUDE.md`](CLAUDE.md).

---

## 🗺️ Roadmap

### ✅ Implementado
- [x] Infrastructure (Docker, Postgres, Redis, Directus)
- [x] 25+ SQLAlchemy models con migraciones
- [x] Web Monitor: platform detection, signal extraction, auto-discovery
- [x] Suggestion Engine: industry-based competitor recommendations
- [x] SaaS multi-tenant con feature flags
- [x] IMAP Newsletter Monitor: matches emails to competitors

- [x] **📦 Catalog Intelligence** — Tracking de SKU, Precios y Stock para VTEX/Shopify/SFCC/Magento.
- [x] **🧠 AI Briefing System** — Generación de reportes con prompts editables desde la DB.

### 🔮 Fases Futuras
- [ ] **� Multi-Channel Alerts** — Integración con Slack/Discord para alertas de cambios críticos.
- [ ] **👁️ Vision LLM Analysis** — Análisis visual de homepages usando capturas de pantalla.
- [ ] **📊 Dashboard Frontend** — Panel web avanzado con visualizaciones de tendencias.

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
