# Arquitectura del Sistema: Competitive Intelligence Briefing Engine

## 1. Stack Tecnológico (MVP)
- **Base de Datos:** PostgreSQL 16. Fuente de verdad única. Schema gobernado por migraciones (Alembic). Preparado para millones de registros (catálogo futuro).
- **Backoffice / CRUD:** Directus 11. Se conecta a PostgreSQL por introspección. Panel de administración de competidores, planes de suscripción, feature flags, y visualización de datos por el equipo operativo. **El pricing y los planes se configuran directamente desde Directus** editando la tabla `subscription_tier`.
- **Motor / API:** FastAPI 0.115+ (Python 3.12+). Endpoints para consumidores externos y orquestación.
- **Workers:** ARQ (Async Redis Queue) sobre Redis 7. Procesos de background asíncronos para scraping, IMAP, diff, fingerprinting, briefing y auto-suscripción a newsletters.
- **Gestor de Paquetes:** `uv` (Astral).
- **Task Runner:** `Makefile` auto-documentado. El usuario solo escribe `make up`, `make test`, `make db-upgrade`, etc. Sin memorizar comandos.

## 2. Principios de Diseño
1. **Directus-Friendly:** Tablas en `snake_case`, PKs BIGINT, FKs explícitas, `created_at` / `updated_at`. Directus se adapta a la DB, no al revés.
2. **Raw-First:** Todo HTML/email se guarda crudo (Snapshot). La extracción de señales es posterior y reprocesable.
3. **Desacople:** FastAPI no asume Directus. Cualquier consumidor interactúa con la API.
4. **Idempotencia y Tolerancia a Fallos:** Jobs que pueden correr múltiples veces. Errores parciales no detienen la corrida.
5. **Multi-Tenant SaaS:** Competidores globales, clientes vinculados vía `client_competitor`. Feature flags por tier controlan qué tareas se encolan.
6. **Platform-Aware Scraping:** Detección de plataforma eCommerce (VTEX, Shopify, Magento, TiendaNube, WooCommerce, PrestaShop) para enrutar al extractor específico (Strategy Pattern).
