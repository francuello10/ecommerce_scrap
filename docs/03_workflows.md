# Flujos de Trabajo (Workers / Jobs)

El sistema se compone de workers ARQ asíncronos desacoplados. Cada tarea verifica los **Feature Flags** del tier del cliente antes de ejecutarse.

---

## 1. Competitor Onboarding Flow (On-Demand)
1. **Trigger:** Al crear un `competitor` en Directus (o via API).
2. **Verificación SaaS:** Si el dominio ya existe en tabla global → solo vincular `client_competitor` + generar `upsell_event`. No duplicar scraping.
3. **Discovery:** Descarga homepage (HTTPX, fallback Playwright).
4. **Detección de Plataforma:** Capa 1 (heurísticas) → determina VTEX/Shopify/etc.
5. **Auto-Descubrimiento:** Escanea `<header>`, `<nav>`, `<footer>` (NO el body) buscando links a `/promociones`, `/sale`, `/financiacion`, etc. Crea `monitored_page` con `discovery_method = AUTO`.
6. **Primer Snapshot + Extracción:** Primer `page_snapshot` + `detected_signal`.
7. **Tech Fingerprint (Background):** `wappalyzer-next` (Capa 2) → `competitor_tech_profile`.
8. **Newsletter Auto-Sub (Best-Effort):** Playwright busca form de newsletter → intenta suscribir la casilla genérica. Si falla → `PENDING_MANUAL`.

## 2. Web Monitoring Flow (Cron)
1. **Trigger:** Cron programado (frecuencia según tier: 1x, 3x, o 6x/día).
2. **Feature Flag Gate:** `subscription_tier` del cliente determina si se ejecuta.
3. **Platform-Aware Scraping:** `ExtractorFactory.create(platform)` instancia el extractor específico (VTEX, Shopify, etc.) o `GenericHtmlExtractor` como fallback.
4. **Self-Healing:** Si el extractor falla (ej. VTEX `__STATE__` no encontrado), marca `is_valid = False` y recalibra con Capa 1.
5. **Almacenamiento:** Guarda HTML crudo en disco/S3 + `page_snapshot`.
6. **Extracción:** Señales comerciales → `detected_signal`.

## 3. Newsletter Ingestion Flow (Cron)
1. **Trigger:** Cron frecuente (cada 15 min). **Gate:** `can_track_newsletters`.
2. **Conexión IMAP:** Conecta a las `newsletter_account` via `imap-tools`.
3. **Detección Double Opt-in:** Si el asunto contiene "Confirma tu suscripción" → extrae link de confirmación → lo visita en background → marca `newsletter_subscription.status = ACTIVE`.
4. **Lectura Normal:** Filtra correos no leídos, matchea al competidor por dominio del remitente.
5. **Extracción:** Parsea HTML con BS4, extrae señales con misma taxonomía que web.

## 4. Diff Engine Flow (Cascada)
1. **Trigger:** Se ejecuta en cascada después de la extracción web o de emails.
2. **Comparación:** Set actual de `detected_signal` vs snapshot anterior.
3. **Relevancia:** Filtra falsos positivos (tokens, IDs rotativos). Asigna `severity`.
4. **Alertas Inmediatas:** Si `severity = CRITICAL` (ej. Flash Sale) y `can_use_realtime_alerts = True` → dispara webhook Slack/Discord.

## 5. Briefing Flow (Cron Diario)
1. **Trigger:** Cron diario (08:30 AM). **Gate:** brief semanal requiere `can_generate_weekly_brief`.
2. **Consolidación:** Recolecta `change_event` + `newsletter_message` de las últimas 24h.
3. **Baseline Comparison:** Si el cliente tiene `is_baseline = True` en un `client_competitor`, genera sección "Tu marca vs la competencia".
4. **Generación:** Aplica reglas de formato / LLM para tono accionable.
5. **Publicación:** `daily_brief` en Markdown + JSON.

## 6. Tech Fingerprint Flow (Cron Semanal)
1. **Trigger:** Cron semanal (Domingos 03:00 AM). **Gate:** `can_track_tech_stack`.
2. **Deep Scan:** `wappalyzer-next` (Capa 2) para todos los competidores activos.
3. **Diff de Stack:** Compara con `competitor_tech_profile` anterior.
4. **Cambio Detectado:** INSERT en `tech_profile_history` + `tech_profile_change` + alerta Slack si es categoría crítica (ej. sumó Connectif).
