# Modelo de Negocio SaaS: Multi-Tenant, Feature Flags y Upsell

---

## 1. Modelo Multi-Tenant: La Tabla Intermedia `client_competitor`

### Principio
La tabla `competitor` es **global** (propiedad del sistema). Los clientes (agencias, marcas) se vinculan a ella a través de `client_competitor`. Un mismo competidor puede ser monitoreado por N clientes sin duplicar scraping.

### Tabla: `client_competitor`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `client_id` | FK → `client` | El cliente/agencia que se vincula |
| `competitor_id` | FK → `competitor` | El competidor global |
| `is_baseline` | BOOLEAN | **`True` = "Esta es MI empresa".** Habilita reportes "Nosotros vs Ellos". |
| `priority` | VARCHAR | HIGH, MEDIUM, LOW (overridea el default global para este cliente) |
| `history_access_start_date` | TIMESTAMP | Desde qué fecha puede leer snapshots/señales. **Llave del Upsell.** |
| `notes` | TEXT | Notas privadas del cliente sobre este competidor |
| `added_at` | TIMESTAMP | Cuándo se vinculó |

> **Constraint:** UNIQUE(`client_id`, `competitor_id`) — Un cliente no puede vincular el mismo competidor dos veces.

### El campo `is_baseline`

Cuando un cliente marca un competidor como `is_baseline = True`:
- Este competidor es **su propia marca/empresa**.
- Los briefs incluyen una sección comparativa: **"Tu marca vs la competencia"**.
- Las métricas se relativizan: *"Tu frecuencia promocional es 40% menor que el promedio del mercado"*.

```
Ejemplo: Cliente "Dexter" configura:

  client_competitor: [
    { competitor: "Newsport",  is_baseline: false, priority: HIGH },
    { competitor: "Sporting",  is_baseline: false, priority: MEDIUM },
    { competitor: "Dexter",    is_baseline: true,  priority: HIGH },  ← "SOY YO"
  ]

Brief generado:
  "📊 Dexter (tu marca) lanzó 2 promos esta semana.
   Newsport lanzó 5 promos (+150% más agresivo).
   Sporting lanzó 3 promos (+50% más agresivo)."
```

---

## 2. Feature Flags y Tiers de Pricing

### Tabla: `subscription_tier`

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `name` | VARCHAR UNIQUE | `BASIC`, `PROFESSIONAL`, `ENTERPRISE` |
| `max_competitors` | INTEGER | Límite de competidores vinculados |
| `max_monitored_pages` | INTEGER | Límite global de páginas por competidor |
| `monitoring_frequency` | VARCHAR | LOW (1x/día), MEDIUM (3x/día), HIGH (6x/día) |
| `can_track_newsletters` | BOOLEAN | Ingesta y análisis de newsletters |
| `can_track_tech_stack` | BOOLEAN | Fingerprinting de stack + change detection |
| `can_track_catalog` | BOOLEAN | Scraping de catálogo completo (Fase 2) |
| `can_use_realtime_alerts` | BOOLEAN | Alertas Slack/Webhook inmediatas |
| `can_access_api` | BOOLEAN | Acceso a la API de FastAPI |
| `can_generate_weekly_brief` | BOOLEAN | Brief semanal con tendencias |
| `can_use_baseline_comparison` | BOOLEAN | Reportes "Nosotros vs Ellos" |
| `history_retention_days` | INTEGER | Días de retención de histórico (ej. 30, 90, 365, -1 = ilimitado) |
| `price_monthly_usd` | DECIMAL | Precio mensual |
| `created_at` | TIMESTAMP | |

### Planes Propuestos

| Feature | 🟢 BASIC | 🔵 PROFESSIONAL | 🟣 ENTERPRISE |
| :--- | :---: | :---: | :---: |
| Competidores | 3 | 10 | Ilimitados |
| Páginas por competidor | 5 | 20 | Ilimitadas |
| Frecuencia de monitoreo | 1x/día | 3x/día | 6x/día |
| Newsletter tracking | ❌ | ✅ | ✅ |
| Tech Stack fingerprinting | ❌ | ✅ | ✅ |
| Catálogo completo (Fase 2) | ❌ | ❌ | ✅ |
| Alertas en tiempo real | ❌ | ✅ | ✅ |
| Acceso API | ❌ | ❌ | ✅ |
| Brief semanal | ❌ | ✅ | ✅ |
| Comparación Baseline | ❌ | ❌ | ✅ |
| Retención de histórico | 30 días | 90 días | Ilimitado |
| **Precio/mes** | **$49** | **$149** | **$499+** |

### Relación: `client.tier_id` → `subscription_tier`

La tabla `client` se actualiza con:

| Campo adicional | Tipo | Descripción |
| :--- | :--- | :--- |
| `tier_id` | FK → `subscription_tier` | El plan actual del cliente |
| `trial_ends_at` | TIMESTAMP | Fin del período de prueba (nullable) |
| `billing_status` | VARCHAR | `TRIAL`, `ACTIVE`, `PAST_DUE`, `CANCELLED` |

---

## 3. Cómo el Orquestador Usa los Feature Flags

El orquestador (FastAPI + ARQ) **consulta los flags del tier del cliente ANTES de encolar tareas**. Esto controla costos de infraestructura:

```python
# Pseudocódigo del Orquestador

async def schedule_competitor_tasks(client: Client, competitor: Competitor):
    tier = client.tier  # → subscription_tier

    # SIEMPRE se ejecuta: scraping web básico
    await enqueue("web_monitor", competitor_id=competitor.id)

    # Solo si el plan lo permite
    if tier.can_track_newsletters:
        await enqueue("newsletter_monitor", competitor_id=competitor.id)

    if tier.can_track_tech_stack:
        await enqueue("tech_fingerprint", competitor_id=competitor.id)

    if tier.can_track_catalog:
        await enqueue("catalog_scraper", competitor_id=competitor.id)  # Fase 2

    if tier.can_use_realtime_alerts:
        await enqueue("alert_dispatcher", competitor_id=competitor.id)
```

### Restricción de Recursos Costosos

| Tarea | Recurso costoso | Controlado por |
| :--- | :--- | :--- |
| `newsletter_monitor` | Conexión IMAP + Playwright (auto-sub) | `can_track_newsletters` |
| `tech_fingerprint` | Análisis wappalyzer-next + storage | `can_track_tech_stack` |
| `catalog_scraper` | Millones de requests + storage masivo | `can_track_catalog` |
| `alert_dispatcher` | Webhook Slack / notificaciones push | `can_use_realtime_alerts` |

> **Sin el flag activo, la tarea no se encola.** Esto evita que un cliente en plan BASIC consuma recursos de Playwright o de fingerprinting.

---

## 4. El Flujo de Upsell Histórico

### Regla de Negocio

> Si un cliente agrega un `domain` que ya existe en la tabla global `competitor` desde hace meses, el sistema **crea la relación** pero fija `history_access_start_date` al **día de hoy**, restringiendo el acceso a datos anteriores. Automáticamente genera un evento de upsell.

### Flujo Detallado

```
Cliente "Dexter" quiere monitorear "newsport.com.ar"
    │
    ├── ¿Existe "newsport.com.ar" en la tabla global competitor?
    │
    ├── SÍ (existe desde hace 6 meses, tiene 180 snapshots acumulados)
    │   │
    │   ├── 1. Crear client_competitor:
    │   │       client_id = Dexter
    │   │       competitor_id = Newsport
    │   │       history_access_start_date = 2026-02-24 (HOY)
    │   │       ← Solo puede ver datos desde hoy en adelante
    │   │
    │   ├── 2. Generar evento UPSELL:
    │   │       {
    │   │         type: "HISTORICAL_DATA_AVAILABLE",
    │   │         client_id: "Dexter",
    │   │         competitor: "Newsport",
    │   │         data_since: "2025-08-24",
    │   │         snapshots_available: 180,
    │   │         signals_available: 1240,
    │   │         message: "Tenemos 6 meses de historial de Newsport.
    │   │                   ¿Desea desbloquear el acceso completo?"
    │   │       }
    │   │
    │   ├── 3. Notificación al equipo comercial (Slack / email interno)
    │   │
    │   └── 4. NO duplicar scraping (ya corre por otros clientes)
    │
    └── NO (dominio nuevo)
        └── Crear competitor + disparar Job de Onboarding completo
```

### Desbloqueo del Historial (Post-Venta)

Cuando el cliente paga por el upsell:

```python
# Un admin actualiza en Directus:
client_competitor.history_access_start_date = "2025-08-24"  # 6 meses atrás

# A partir de ese momento, las queries del cliente incluyen el pasado:
SELECT * FROM page_snapshot ps
  JOIN monitored_page mp ON ps.monitored_page_id = mp.id
  WHERE mp.competitor_id = :competitor_id
    AND ps.created_at >= :history_access_start_date  ← filtro clave
```

### Tabla de Eventos de Upsell

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `client_id` | FK → `client` | |
| `competitor_id` | FK → `competitor` | |
| `event_type` | VARCHAR | `HISTORICAL_DATA_AVAILABLE`, `TIER_UPGRADE_SUGGESTED` |
| `data_available_since` | DATE | Desde cuándo hay datos acumulados |
| `snapshots_count` | INTEGER | Cantidad de snapshots disponibles |
| `signals_count` | INTEGER | Cantidad de señales detectadas |
| `status` | VARCHAR | `PENDING`, `OFFERED`, `ACCEPTED`, `DECLINED` |
| `created_at` | TIMESTAMP | |
| `resolved_at` | TIMESTAMP | Cuándo se cerró (nullable) |

---

## 5. Diagrama de Relaciones Completo (SaaS)

```
subscription_tier
    │ 1:N
    ▼
  client ──N:N──▶ client_competitor ◀──N:N── competitor (GLOBAL)
    │                │    │                        │
    │           is_baseline?              ┌────────┤
    │           history_access            │        │
    │                                monitored  tech_profile
    │                                  _page       (1:1)
    ├── upsell_event                     │
    │                              page_snapshot
    └── newsletter_account               │
            │                      detected_signal
        newsletter                       │
        _subscription              change_event
            │                            │
        newsletter               daily_brief
        _message                         │
                                  weekly_brief
```
