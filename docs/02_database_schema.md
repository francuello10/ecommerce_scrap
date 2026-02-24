# Esquema de Base de Datos (Directus-Friendly) — Multi-Tenant SaaS

*Nota: Este es el modelo conceptual. Se implementará vía migraciones (Alembic).*

---

## 0. Tablas de Tenancy / SaaS (Multi-Inquilino)

- `subscription_tier` (id, name UNIQUE [BASIC, PROFESSIONAL, ENTERPRISE], max_competitors, max_monitored_pages, monitoring_frequency, can_track_newsletters BOOL, can_track_tech_stack BOOL, can_track_catalog BOOL, can_use_realtime_alerts BOOL, can_access_api BOOL, can_generate_weekly_brief BOOL, can_use_baseline_comparison BOOL, history_retention_days, price_monthly_usd DECIMAL)
- `client` (id, name, slug, contact_email, tier_id FK→subscription_tier, billing_status [TRIAL, ACTIVE, PAST_DUE, CANCELLED], trial_ends_at, is_active, created_at, updated_at)
- `client_competitor` (id, client_id FK→client, competitor_id FK→competitor, **is_baseline** BOOL, priority [HIGH, MEDIUM, LOW], **history_access_start_date** TIMESTAMP, notes, added_at)
  - *Relación N:N. `is_baseline = True` indica "esta es MI empresa" (habilita reportes comparativos). `history_access_start_date` controla el acceso al histórico (llave de upsell).*
- `upsell_event` (id, client_id FK, competitor_id FK, event_type [HISTORICAL_DATA_AVAILABLE, TIER_UPGRADE_SUGGESTED], data_available_since DATE, snapshots_count, signals_count, status [PENDING, OFFERED, ACCEPTED, DECLINED], created_at, resolved_at)

> **Regla de negocio:** Al intentar dar de alta un `competitor` con un `domain` que ya existe, el sistema:
> 1. NO crea un nuevo scraper.
> 2. Vincula al `client` con el `competitor` existente vía `client_competitor`.
> 3. Genera un evento `UPSELL_OPPORTUNITY` ofreciendo acceso al histórico de datos ya recolectados.

---

## 1. Tablas de Configuración (Editables mediante Directus)

- `competitor` (id, name, domain UNIQUE, vertical, country, status [PENDING_ONBOARDING, ACTIVE, PAUSED, ERROR], onboarded_at, created_at, updated_at)
  - *Tabla GLOBAL del sistema. No pertenece a un cliente específico.*
- `monitored_page` (id, competitor_id FK, url, page_type [HOMEPAGE, PROMO_PAGE, FINANCING_PAGE, SHIPPING_PAGE, CATEGORY, OTHER], discovery_method [AUTO, MANUAL], is_active, created_at)
- `newsletter_account` (id, email_address, imap_host, imap_port, mailbox_config_json, is_active)
- `newsletter_subscription` (id, competitor_id FK, newsletter_account_id FK, status [PENDING_AUTO, PENDING_OPTIN, PENDING_MANUAL, ACTIVE, FAILED], auto_sub_attempts, last_attempt_at, confirmed_at, created_at)
- `signal_taxonomy` (id, name, type [PROMO, FINANCIACION, ENVIO, URGENCIA, CTA, BRAND_HIGHLIGHT], description)

---

## 2. Tablas Raw / Operativas (Solo Lectura/Auditoría en Directus)

- `crawl_run` (id, started_at, ended_at, status [RUNNING, SUCCESS, FAILED_PARTIAL])
- `page_snapshot` (id, monitored_page_id FK, run_id FK, raw_storage_path, status [PENDING_EXTRACTION, EXTRACTED, ERROR], created_at)
- `newsletter_message` (id, competitor_id FK, newsletter_account_id FK, sender_email, subject, received_at, raw_html_path, is_optin_confirmation BOOLEAN, status)
- `job_execution_log` (id, job_type, started_at, ended_at, status, items_processed, error_message)

---

## 3. Tablas de Catálogo (Fase 2 / Preparación)

- `product` (id, competitor_id FK, sku, url, brand, title, description, images JSONB, category_path, category_tree JSONB, financing_options JSONB, discovered_from, rating_avg DECIMAL, review_count INT, badges JSONB, is_active, first_seen_at)
- `product_variant` (id, product_id FK, sku, title, is_in_stock, list_price, sale_price, raw_metadata JSONB, created_at, updated_at)
- `price_history` (id, product_id FK, snapshot_id FK, product_variant_id FK, list_price, sale_price, currency, is_in_stock, recorded_at)

---

## 4. Tablas de Resultados / Procesadas

- `detected_signal` (id, source_type [WEB, EMAIL], source_id, taxonomy_id FK, raw_text_found, confidence_score, created_at)
- `change_event` (id, competitor_id FK, event_type [NEW_PROMO, REMOVED_PROMO, CHANGED_HERO, CHANGED_FINANCING, FLASH_SALE], severity [LOW, MEDIUM, HIGH, CRITICAL], old_value, new_value, created_at)

---

## 5. Tablas de Tech Fingerprinting

- `competitor_tech_profile` (id, competitor_id FK UNIQUE, ecommerce_platform, platform_version, analytics_tools JSONB, marketing_automation JSONB, tag_managers JSONB, payment_gateways JSONB, live_chat JSONB, cdn_provider, js_frameworks JSONB, full_fingerprint_json JSONB, is_valid BOOLEAN, last_fingerprinted_at, updated_at)
- `tech_profile_history` (id, competitor_id FK, snapshot_date DATE, ecommerce_platform, full_fingerprint_json JSONB, created_at)
- `tech_profile_change` (id, competitor_id FK, detected_at, change_type [ADDED, REMOVED, CHANGED], category, tool_name, previous_value, new_value)

---

## 6. Tablas de Entrega / Briefs

- `daily_brief` (id, brief_date, content_markdown, content_json, status [DRAFT, PUBLISHED], created_at)
- `weekly_brief` (id, start_date, end_date, content_markdown, content_json, created_at)

---

## Diagrama de Relaciones Clave

```
client ──N:N──▶ client_competitor ◀──N:N── competitor (GLOBAL)
                                               │
                    ┌──────────────────────────┤
                    │              │            │
              monitored_page   newsletter   competitor_tech_profile (1:1)
                    │          _subscription        │
              page_snapshot        │          tech_profile_history (1:N)
                    │         newsletter
              detected_signal  _message
                    │
              change_event ──▶ daily_brief ──▶ weekly_brief
```
