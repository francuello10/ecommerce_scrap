# Flujo Operativo: De "Dar de Alta un Competidor" al Brief Diario

## 1. La Filosofía: "Una URL y el Sistema Hace el Resto"

El objetivo es que un analista (o una agencia cliente SaaS) pueda dar de alta un competidor con el **mínimo input posible** y que el sistema se encargue de descubrir, clasificar y empezar a monitorear automáticamente.

**Input mínimo del usuario:** Solo el dominio (ej. `newsport.com.ar`).
**Todo lo demás:** Lo infiere el sistema.

---

## 2. Modelo Multi-Tenant (SaaS)

Los competidores son **entidades globales** del sistema. Cuando un cliente (agencia, marca) da de alta un competidor:

```
¿El dominio "newsport.com.ar" ya existe en la tabla global `competitor`?
    │
    ├── NO → Crear competitor + disparar Job de Onboarding completo
    │
    └── SÍ → Solo crear el vínculo client_competitor
              ├── El cliente accede a los datos que ya se recolectan
              ├── No se duplica scraping (eficiencia)
              └── Evento UPSELL: "Tenemos 6 meses de histórico, ¿querés acceso?"
```

---

## 3. Flujo Completo (Paso a Paso)

### PASO 1 — Alta del Competidor (En Directus, ~30 segundos)

El usuario abre Directus → Colección `competitor` → "Crear Nuevo" y llena:

| Campo | ¿Obligatorio? | Ejemplo | ¿Por qué? |
| :--- | :--- | :--- | :--- |
| `domain` | ✅ Sí | `newsport.com.ar` | Es lo único que el sistema necesita para arrancar |
| `name` | ✅ Sí | `Newsport` | Para que aparezca legible en los briefs |
| `vertical` | ⬜ Opcional | `DEPORTES` | Para agrupar en briefs ("competidores de deportes hicieron X") |
| `country` | ⬜ Opcional | `AR` | Para contexto regional |
| `notes` | ⬜ Opcional | "Competidor directo en running" | Notas libres para el analista |

> **Nada más.** No necesita poner URLs específicas, ni decir qué plataforma usa, ni configurar extractores.

### PASO 2 — Onboarding Automático (Job "Discovery", ~2 minutos)

Al guardar el competidor, el sistema dispara automáticamente un **job de onboarding**:

```
🤖 Job: competitor_onboarding(domain="newsport.com.ar")
    │
    ├── 1. Visita https://newsport.com.ar (HTTPX + fallback Playwright)
    │
    ├── 2. Detección de Plataforma
    │   ├── Capa 1 (heurísticas) → "VTEX detectado"
    │   └── Capa 2 (wappalyzer-next, background) → perfil completo
    │
    ├── 3. Auto-Descubrimiento de Páginas Clave
    │   │
    │   │  ⚠️ RESTRICCIÓN: Solo se escanean las zonas de HEADER y FOOTER
    │   │  del HTML, NO el body completo. Esto evita ruido y links irrelevantes.
    │   │
    │   ├── Busca <header>, <nav>, <footer> (HTML5 semántico)
    │   ├── Fallback: busca selectores por plataforma:
    │   │   ├── VTEX:      .vtex-menu, .vtex-footer
    │   │   ├── Shopify:   #shopify-section-header, #shopify-section-footer
    │   │   ├── Magento:   .nav-sections, .footer.content
    │   │   ├── TiendaNube: .js-nav, .js-footer
    │   │   └── Genérico:  nav, [role="navigation"], footer, .footer
    │   │
    │   ├── De los links encontrados, clasifica automáticamente:
    │   │   ├── /promociones, /ofertas, /sale, /outlet     → PROMO_PAGE
    │   │   ├── /financiacion, /cuotas, /bancos            → FINANCING_PAGE
    │   │   ├── /envios, /envio-gratis                     → SHIPPING_PAGE
    │   │   └── Links de categorías principales del nav    → CATEGORY
    │   │
    │   └── Crea registros en `monitored_page` con discovery_method = AUTO
    │
    ├── 4. Primer Snapshot
    │   └── Guarda el HTML crudo de la home como primer page_snapshot
    │
    ├── 5. Primera Extracción
    │   └── Corre el extractor adecuado (ej. VtexExtractor)
    │       y guarda las primeras detected_signal
    │
    ├── 6. Intento de Suscripción a Newsletter (Best-Effort)
    │   └── (ver sección de Newsletters más abajo)
    │
    └── 7. Actualiza el estado
        ├── competitor.status = "ACTIVE"
        ├── competitor_tech_profile → lleno
        └── Listo para monitoreo diario
```

### PASO 3 — Revisión por el Analista (En Directus, ~1 minuto)

El usuario vuelve a Directus y ve:

```
📋 Competidor: Newsport
├── Estado: ✅ ACTIVE
├── Plataforma: VTEX IO
├── Tech Profile: GA4, Connectif, WhatsApp Business, Cloudflare
│
├── 📄 Páginas Monitoreadas (auto-descubiertas del header/footer):
│   ├── ✅ https://newsport.com.ar/                    [HOMEPAGE]
│   ├── ✅ https://newsport.com.ar/promociones         [PROMO_PAGE]
│   ├── ✅ https://newsport.com.ar/sale                [PROMO_PAGE]
│   ├── ✅ https://newsport.com.ar/financiacion        [FINANCING_PAGE]
│   └── ⬜ https://newsport.com.ar/running             [CATEGORY]
│
├── 📧 Newsletter: PENDING_OPTIN (esperando confirmación del email)
│
└── 📸 Primer Snapshot: 2026-02-24 01:00 AM
    └── Señales detectadas: 3 promos, 2 financiación, 1 envío gratis
```

> **⚠️ IMPORTANTE para el analista:** El auto-discovery solo busca en el header/footer.
> Si el competidor tiene una landing de promociones NO linkeada en el menú principal
> (ej. una URL armada para Google Ads), el analista **debe agregarla manualmente**
> en Directus como `monitored_page` con `discovery_method = MANUAL`.

**El usuario puede:**
- ✅ Dejar todo como está (el sistema ya sabe qué monitorear)
- ➕ Agregar manualmente URLs que el auto-discovery no encontró
- ❌ Desactivar una página que no le interesa
- 📝 Cambiar la prioridad del competidor

### PASO 4 — El Sistema Corre Solo (Todos los días, automáticamente)

```
⏰ Cron Diario (ej. 06:00 AM, 12:00 PM, 18:00 PM)
    │
    ├── Para cada competitor ACTIVE:
    │   ├── Para cada monitored_page activa:
    │   │   ├── Descarga → Snapshot → Extrae señales
    │   │   └── Compara vs snapshot anterior → Detecta cambios
    │   │
    │   └── Si hay cambio urgente → Alerta Slack inmediata
    │
    ├── 08:30 AM → Genera Brief Diario
    │   └── Consolida todos los cambios de las últimas 24h
    │   └── Lo guarda en daily_brief (Markdown + JSON)
    │
    └── Lunes 08:00 AM → Genera Brief Semanal
```

### PASO 5 — El Usuario Consume (Directus + Slack + API)

```
📊 El analista tiene 3 canales de consumo:

1. DIRECTUS (Panel - Exploración profunda)
   └── Ve snapshots, señales, histórico, tech profiles

2. SLACK (Alertas - Reacción inmediata)
   └── "🚨 Newsport lanzó Flash Sale 50% OFF en Running"

3. API FastAPI (Integración - Futuro)
   └── Odoo, BI, o cualquier sistema consume /api/briefs
```

---

## 4. Newsletter Monitor (Flujo con Auto-Suscripción Best-Effort)

### 4a. Setup Inicial (una sola vez)

1. Se configura en Directus una `newsletter_account` con una casilla de correo dedicada (ej. `radar@agencia.com`) y sus credenciales IMAP.
2. Esta casilla será la que se use para suscribirse a los newsletters de todos los competidores.

### 4b. Auto-Suscripción (Best-Effort con Playwright)

Cuando se da de alta un competidor, el job de onboarding incluye un **intento automático de suscripción**:

```
🤖 Job: newsletter_auto_subscribe(domain="newsport.com.ar", email="radar@agencia.com")
    │
    ├── 1. Abre la homepage con Playwright (browser headless)
    │
    ├── 2. Busca formularios de newsletter en el DOM:
    │   ├── input[type="email"] cerca de textos como "newsletter",
    │   │   "suscribite", "novedades", "ofertas"
    │   ├── Formularios en footer (zona más común)
    │   └── Popups de suscripción (si aparecen)
    │
    ├── 3. Intenta rellenar el email y hacer submit
    │   │
    │   ├── ✅ Submit exitoso →
    │   │   ├── newsletter_subscription.status = "PENDING_OPTIN"
    │   │   └── Espera email de confirmación (double opt-in)
    │   │
    │   └── ❌ Falla (CAPTCHA, JS complejo, no encontró form) →
    │       ├── newsletter_subscription.status = "PENDING_MANUAL"
    │       ├── auto_sub_attempts += 1
    │       └── Alerta en Directus: "Suscripción manual requerida para Newsport"
    │
    └── 4. Se registra en newsletter_subscription con el estado correspondiente
```

### 4c. Confirmación Automática de Double Opt-in

El lector IMAP tiene una regla especial para detectar emails de confirmación:

```
🤖 Regla IMAP: detect_optin_confirmation
    │
    ├── Busca emails con asuntos que contengan:
    │   ├── "Confirma tu suscripción"
    │   ├── "Confirm your subscription"
    │   ├── "Verificá tu email"
    │   ├── "Activá tu cuenta"
    │   └── (regex configurable por idioma)
    │
    ├── Extrae el link de confirmación del body HTML
    │   └── Busca <a> con textos como "Confirmar", "Confirm", "Activar"
    │
    ├── Visita el link en background (HTTPX o Playwright)
    │
    └── Actualiza newsletter_subscription:
        ├── status = "ACTIVE"
        └── confirmed_at = now()
```

### 4d. Auto-Vinculación de Emails Entrantes

```
Email entrante: newsletter@newsport.com.ar
    │
    ├── ¿El dominio "newsport.com.ar" matchea algún competitor.domain?
    │   ├── SÍ → Vincula automáticamente a competitor_id
    │   └── NO → Marca como "unmatched" para revisión manual en Directus
    │
    └── Parsea contenido → Extrae señales → Almacena en newsletter_message
```

---

## 5. Resumen: ¿Qué Hace el Usuario vs Qué Hace el Sistema?

| Acción | ¿Quién? | ¿Cuándo? |
| :--- | :--- | :--- |
| Escribir dominio + nombre del competidor | 👤 Usuario | Una sola vez |
| Detectar plataforma (VTEX, Shopify, etc.) | 🤖 Sistema | Auto al guardar |
| Descubrir páginas clave (header/footer) | 🤖 Sistema | Auto al guardar |
| Primer snapshot + extracción de señales | 🤖 Sistema | Auto al guardar |
| Intentar suscripción a newsletter | 🤖 Sistema | Auto al guardar (best-effort) |
| Confirmar double opt-in | 🤖 Sistema | Auto al recibir email |
| Revisar y ajustar páginas descubiertas | 👤 Usuario | Opcional, ~1 min |
| Suscribirse manualmente (si CAPTCHA) | 👤 Usuario | Solo si auto-sub falló |
| Agregar URLs no descubiertas | 👤 Usuario | Cuando quiera, raro |
| Monitoreo diario completo | 🤖 Sistema | Cron automático |
| Generar brief diario/semanal | 🤖 Sistema | Cron automático |
| Alertas urgentes (Slack) | 🤖 Sistema | Tiempo real |
| Leer brief y tomar decisiones | 👤 Usuario | Cada mañana |
