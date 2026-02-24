# Tech Fingerprinting: Detección de Stack de Competidores (Estilo Wappalyzer)

## 1. El Problema
No nos basta con saber *qué* muestra el competidor; necesitamos saber **con qué está armado**: plataforma de eCommerce, analytics, pasarelas de pago, CDN, frameworks JS, chat en vivo, etc. Esto nos permite:

- **Predecir velocidad de reacción:** Un competidor en VTEX IO (headless, deploy rápido) puede cambiar su home en minutos. Uno en Magento 2 on-premise probablemente tarda horas o días. Si sabemos esto, reaccionamos acorde.
- **Adaptar nuestros extractors:** Si detectamos VTEX, usamos una estrategia de scraping. Si detectamos Shopify, usamos otra.
- **Benchmarking tecnológico:** ¿Usan Hotjar? ¿Google Analytics 4 o Universal? ¿Facebook Pixel? ¿WhatsApp Business Chat? Todo esto es inteligencia accionable.

---

## 2. Opciones Evaluadas (Gratis / Open Source)

| Herramienta | Descripción | Costo | Veredicto |
| :--- | :--- | :--- | :--- |
| **Wappalyzer (extensión/API oficial)** | La más conocida. La extensión de browser es gratis. La API paga arranca en ~$250/mes. | Free (extensión) / Pago (API) | ❌ La API es cara para MVP. La extensión no es scripteable. |
| **`wappalyzer-next`** (Python, de s0md3v) | Librería Python open-source que usa los **fingerprints oficiales de Wappalyzer** (actualizados). Funciona como librería y CLI. GPLv3. | **100% Gratis** | ✅ **Nuestra elección principal.** |
| **`python-Wappalyzer`** (PyPI) | Otra librería Python, pero actualizada por última vez en 2020. Fingerprints desactualizados. | Gratis | ⚠️ Desactualizada, no recomendada. |
| **`EcommercePlatformDetector`** | Librería Python específica para detectar plataformas de eCommerce (VTEX, Shopify, Magento, etc.). Ligera. | Gratis | ✅ Complemento útil si `wappalyzer-next` falla en detección eCommerce específica. |

---

## 3. Estrategia de Implementación Recomendada

### Enfoque: "Doble Capa" de Detección

```
Capa 1: Heurísticas Propias (velocidad máxima, costo cero)
└── Analiza headers HTTP + HTML buscando firmas conocidas:
    ├── VTEX:      `__STATE__`, `vtex.render-server`, header `x-vtex-*`
    ├── Shopify:   `window.Shopify`, `cdn.shopify.com`, header `x-shopify-stage`
    ├── Magento 2:  `Magento/`, `mage-cache-storage`, `requirejs`
    ├── TiendaNube: `tiendanube.com/scripts`, `window.LS`
    ├── WooCommerce: `woocommerce`, `wp-content/plugins/woocommerce`
    └── PrestaShop:  `prestashop`, `var prestashop`

Capa 2: wappalyzer-next (deep fingerprinting completo)
└── Después del scraping, pasa el HTML + headers por wappalyzer-next
    para obtener el stack completo:
    ├── Analytics (GA4, Hotjar, Clarity, FB Pixel)
    ├── Tag Managers (GTM)
    ├── Live Chat (WhatsApp Business, Zendesk, Intercom)
    ├── CDN (Cloudflare, Fastly, AWS CloudFront)
    ├── Payment Gateways (MercadoPago, Stripe)
    └── JS Frameworks (React, Vue, Angular, jQuery)
```

### ¿Por qué doble capa?
- La **Capa 1** corre en milisegundos y es lo que usamos para **enrutar al extractor correcto** (el Platform-Aware Scraping que ya diseñamos).
- La **Capa 2** corre después del scrape y nos da el **perfil tecnológico completo** del competidor, que guardamos en la BD para análisis comparativo.

---

## 4. Modelo de Datos: Opción B (Tablas Separadas)

> **Decisión arquitectónica:** Usamos **tablas separadas** (1:1 para estado actual + 1:N para historial).
> Esto garantiza limpieza en Directus, integridad transaccional y queries rápidas.

### Tabla 1:1 — `competitor_tech_profile` (Estado Actual)
*Lo que el equipo de Marketing ve al abrir un competidor en Directus.*

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `competitor_id` | FK → `competitor` UNIQUE | Relación 1:1 estricta |
| `ecommerce_platform` | VARCHAR | VTEX, SHOPIFY, MAGENTO2, etc. |
| `platform_version` | VARCHAR | Ej. "VTEX IO", "Magento 2.4.6" |
| `analytics_tools` | JSONB | `["GA4", "Hotjar", "Clarity"]` |
| `marketing_automation` | JSONB | `["Connectif", "Synerise"]` |
| `tag_managers` | JSONB | `["GTM"]` |
| `payment_gateways` | JSONB | `["MercadoPago", "Stripe"]` |
| `live_chat` | JSONB | `["WhatsApp Business Chat"]` |
| `cdn_provider` | VARCHAR | Cloudflare, Fastly, etc. |
| `js_frameworks` | JSONB | `["React 18", "jQuery 3.x"]` |
| `full_fingerprint_json` | JSONB | Output completo de `wappalyzer-next` |
| `is_valid` | BOOLEAN | `False` si el extractor falló y necesita recalibración |
| `last_fingerprinted_at` | TIMESTAMP | Última ejecución exitosa de Capa 2 |
| `updated_at` | TIMESTAMP | |

### Tabla 1:N — `tech_profile_history` (Bitácora / Log de Evolución)
*Append-only. Se inserta un registro SOLO cuando el cron semanal detecta un cambio.*

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `competitor_id` | FK → `competitor` | |
| `snapshot_date` | DATE | Fecha del fingerprint semanal |
| `ecommerce_platform` | VARCHAR | La plataforma en ese momento |
| `full_fingerprint_json` | JSONB | Foto completa del stack en ese instante |
| `created_at` | TIMESTAMP | |

> **En Directus:** El usuario abre un competidor → ve el `tech_profile` actual (1:1, limpio).
> Si quiere ver la evolución → click en la pestaña "Historial Tecnológico" → timeline 1:N.

---

## 5. Orquestación Híbrida (Diario + Semanal)

### Flujo Diario (Self-Healing)
```
Orquestador recibe monitored_page
    │
    ├── Consulta competitor_tech_profile (1:1)
    │   └── ecommerce_platform = "VTEX", is_valid = True
    │
    ├── ExtractorFactory.create("VTEX") → VtexExtractor
    │
    ├── extractor.extract_all(html)
    │   ├── ✅ OK → continúa normal
    │   └── ❌ Tasa de Error alta (no encuentra __STATE__, etc.)
    │       ├── Marca is_valid = False en DB
    │       ├── Corre PlatformDetector (Capa 1) para recalibrarse
    │       └── Usa el nuevo extractor detectado para esta corrida
    │
    └── Guarda señales en detected_signal
```

### Cron Semanal (Deep Fingerprint + Historial)
```
Worker ARQ semanal (ej. Domingos 03:00 AM)
    │
    ├── Para cada competitor activo:
    │   ├── Descarga homepage (HTTPX)
    │   ├── Corre wappalyzer-next (Capa 2) → full_fingerprint_json
    │   │
    │   ├── Compara con competitor_tech_profile.full_fingerprint_json actual
    │   │   ├── Sin cambios → solo actualiza last_fingerprinted_at
    │   │   └── ¡Cambio detectado! →
    │   │       ├── INSERT en tech_profile_history (foto anterior)
    │   │       ├── UPDATE competitor_tech_profile (nueva foto)
    │   │       ├── INSERT en tech_profile_change (diff detallado)
    │   │       └── Dispara alerta Slack si es categoría crítica
    │   │
    │   └── Marca is_valid = True (recalibrado)
```

---

## 5b. Valor para el Brief (CMO)
Con esta data, el brief diario puede incluir una sección como:

> **🔧 Perfil Tecnológico — Newsport.com.ar**
> - Plataforma: **VTEX IO** (deploy rápido, cambios en minutos)
> - Marketing Automation: **Connectif** (personalización activa)
> - Analytics: GA4, Microsoft Clarity, Hotjar
> - Payment: MercadoPago, 3 Cuotas sin interés habilitadas
> - Live Chat: WhatsApp Business
> - CDN: Cloudflare (sitio rápido)
>
> *Insight: Competidor con stack moderno y alta capacidad de reacción. Monitorear con mayor frecuencia.*

---

## 6. Tech Stack Change Detection (Diff de Perfil Tecnológico)

Al correr el fingerprinting de forma periódica (ej. semanal), podemos **comparar el perfil actual contra el anterior** y generar alertas de cambio tecnológico:

### Categorías clave a monitorear
| Categoría | Ejemplos | ¿Por qué importa? |
| :--- | :--- | :--- |
| **Marketing Automation** | Connectif, synerise, Klaviyo, Emarsys, Braze, Drip | Si un competidor suma Connectif, está invirtiendo en personalización y segmentación avanzada |
| **Analytics / CRO** | Hotjar, Clarity, VWO, Optimizely | Indica fase de research UX o testing A/B |
| **Live Chat / CX** | Zendesk, Intercom, Tidio, WhatsApp Business | Cambios en estrategia de atención al cliente |
| **Payment / Checkout** | MercadoPago, Stripe, dLocal, Mobbex | Ampliación de métodos de pago |
| **Email Marketing** | Mailchimp, SendGrid, Mandrill | Migración de proveedor de envíos |
| **Ads / Retargeting** | Google Ads, Meta Pixel, Criteo, RTB House | Inversión en adquisición y remarketing |

### Flujo de detección de cambios
```
1. Fingerprint actual (semana N)     →  { analytics: [GA4, Hotjar], automation: [] }
2. Fingerprint anterior (semana N-1) →  { analytics: [GA4],         automation: [] }
3. Diff:
   ├── ADDED:   Hotjar        → "Competidor inició fase de análisis UX"
   └── REMOVED: (nada)

Semana N+2:
1. Fingerprint actual               →  { analytics: [GA4, Hotjar], automation: [Connectif] }
2. Diff:
   └── ADDED:   Connectif     → "🚨 Competidor sumó Marketing Automation (Connectif)"
```

### Alertas estratégicas en el Brief
Estos cambios se incluirán automáticamente en el brief semanal con contexto:

> **🔄 Cambios Tecnológicos Detectados (Semana 8)**
> | Competidor | Cambio | Herramienta | Insight |
> | :--- | :--- | :--- | :--- |
> | Newsport | ➕ Sumó | **Connectif** | Inversión en personalización y automation |
> | Dexter | ➕ Sumó | **Klaviyo** | Migración de email marketing |
> | Open Sports | ➖ Quitó | **Hotjar** | Terminó fase de research UX |
> | Sporting | 🔄 Cambió | **Zendesk → Intercom** | Reestructuración de soporte |

### Nueva tabla: `tech_profile_change`
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | BIGINT PK | |
| `competitor_id` | FK → `competitor` | |
| `detected_at` | TIMESTAMP | |
| `change_type` | VARCHAR | `ADDED`, `REMOVED`, `CHANGED` |
| `category` | VARCHAR | `AUTOMATION`, `ANALYTICS`, `PAYMENT`, `CHAT`, etc. |
| `tool_name` | VARCHAR | Ej. "Connectif", "Hotjar" |
| `previous_value` | VARCHAR | Null si es `ADDED` |
| `new_value` | VARCHAR | Null si es `REMOVED` |

---

## 7. Dependencia a agregar al `pyproject.toml`

```toml
# Tech fingerprinting
"wappalyzer-next>=0.1.0",
```
