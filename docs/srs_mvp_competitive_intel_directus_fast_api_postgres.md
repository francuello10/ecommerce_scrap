# Prompt maestro para IDE AI (Cursor / Antigravity)

## Rol esperado del asistente de desarrollo
Actúa como **arquitecto de software senior + engineer pragmático** para construir un MVP de inteligencia competitiva orientado a eCommerce.

## Objetivo del desarrollo
Construir un sistema modular y estratégico de Inteligencia Competitiva para retailers y marcas (ej. Moda, Deportes, Electrónica) que permita:
- **monitorear el ecosistema de eCommerce** (VTEX, Magento, Shopify, etc.),
- analizar homepages, páginas promocionales y **futuro catálogo**,
- rastrear comunicaciones enviadas (newsletters),
- generar alertas en tiempo real (Slack/Push) para cambios agresivos,
- consolidar briefs ejecutivos (diarios/semanales),
- y exponer datos operativos/históricos vía API y backoffice (Directus).

## Stack obligatorio (MVP)
- **PostgreSQL** como base de datos principal (preparada para millones de registros: Catálogo + Historia de Precios)
- **Directus** como panel/backoffice ágil
- **FastAPI + workers (ARQ)** como motor de orquestación, scraping y alertas

## Principios de arquitectura (obligatorios)
1. **Separación de responsabilidades**
   - Motor (FastAPI + workers)
   - Persistencia (PostgreSQL)
   - Panel (Directus)
   - Consumidores externos (futuro: Odoo / BI / otros)
2. **Migrable por APIs**
   - Todo módulo relevante debe poder reutilizarse desde otras “mesas de trabajo”/sistemas vía API.
   - No acoplar la lógica de negocio a Directus ni a un panel específico.
3. **Schema gobernado por código**
   - El esquema de DB lo definen migraciones (ej. Alembic).
   - Directus se adapta a la DB existente (no al revés).
4. **Directus-friendly schema**
   - PK simples, FKs explícitas, snake_case, timestamps estándar, tablas separadas entre configuración / raw / resultados.
5. **Raw-first + Reprocesamiento**
   - Guardar snapshots/raw artifacts para poder reprocesar si cambia el extractor.
6. **Observabilidad mínima**
   - Logs estructurados de jobs, errores, duración y cantidad procesada.
7. **Sin Frankenstein**
   - Evitar mezclar scraping dentro del panel.
   - Evitar meter IA/LLM en parsing core antes de estabilizar reglas.

## Buenas prácticas de implementación (obligatorias)
- Python 3.12+
- Tipado estricto (Pydantic / type hints)
- Código modular por dominios (web_monitor, newsletter_monitor, diff, briefing)
- Config por variables de entorno
- Migraciones versionadas
- Tests de regresión con fixtures reales (HTML/emails anonimizados)
- Endpoints con contratos claros (request/response models)
- Jobs idempotentes cuando sea posible
- Reintentos controlados en errores transitorios

## Compatibilidad futura (dejar previsto)
- Integración con Odoo y otros sistemas por API
- Integración con BI (Metabase/Superset/ETL)
- Índice semántico/vectorial futuro (ej. **Zvec**) sin reemplazar PostgreSQL
- Reutilización de componentes existentes del repo **`v0-newsletterAI`** si hay piezas aprovechables

## Cómo trabajar con el repo existente
- Revisar e identificar componentes reutilizables de `v0-newsletterAI`:
  - parsers de emails/newsletters
  - extracción de promos/financiación
  - generador de brief
  - conectores de email/IMAP/Gmail
  - heurísticas/reglas
- Proponer refactor incremental, no reescritura total.
- Mantener compatibilidad funcional mientras se modulariza.

## Entregables esperados del asistente en cada iteración
1. Decisión técnica concreta (con tradeoffs cortos)
2. Código / estructura propuesta
3. Riesgos + mitigación
4. Próximo paso mínimo ejecutable

---

# SRS — Sistema de Inteligencia Competitiva (Scraping + Newsletters + Briefs)

## 1. Información del documento

- **Proyecto:** Competitive Intelligence Briefing Engine
- **Versión del documento:** 0.2 (MVP orientado a Directus)
- **Estado:** Draft para revisión
- **Fecha:** 2026-02-24
- **Owner:** Fran / Equipo interno
- **Tipo:** Software Requirements Specification (SRS)

---

## 2. Propósito

Definir los requisitos funcionales y no funcionales de un sistema que monitoree competidores de eCommerce de forma continua, capturando:

- cambios en homepage y páginas promocionales,
- comunicaciones enviadas por newsletter,
- señales comerciales (promociones, financiación, banners, campañas),
- y resúmenes automáticos (briefs) diarios y semanales.

El sistema debe priorizar:
- **operatividad**,
- **modularidad**,
- **migrabilidad por APIs**,
- **compatibilidad con Directus**,
- y **reutilización de componentes existentes** (especialmente del repo `v0-newsletterAI`).

---

## 3. Alcance

### 3.1 Alcance del MVP (Fase 1)
El MVP incluirá:

1. **Monitoreo Platform-Aware:** Detección de motor subyacente (VTEX, Shopify, Magento) para extracciones robustas de páginas promocionales y homepages.
2. **Ingesta y análisis de newsletters**
3. **Detección de cambios (diff)** y alertas inmediatas (Slack/Webhook)
4. **Generación de brief ejecutivo diario** (Formato CMO)
5. **Esquema de Base de Datos Base de Catálogo:** Preparación de tablas `product` y `price_history` para no romper la BD en Fase 2.
6. **Panel de revisión y operación en Directus**
7. **Persistencia histórica en PostgreSQL**
8. **API en FastAPI** para consumo

### 3.2 Fuera de alcance del MVP (pero previsto en arquitectura)
- Scraping masivo/completo de todo el catálogo (millones de SKUs diarios).
- Trackeo de notificaciones Push (Mobile).
- Integración operativa directa bidireccional con Odoo.
- Índice semántico/vectorial productivo (Zvec).

---

## 4. Objetivos de negocio (Visión CMO)

- **Reducir el Time-to-React:** Pasar de enterarnos el lunes, a reaccionar en horas a un "Special Sale" del competidor.
- **Entender el Shadow Pricing:** Trackear Precio de Lista vs Precio Final a lo largo del tiempo.
- Medir la agresividad promocional, cuotas y convenios bancarios.
- Generar **alertas en tiempo real** y briefs accionables, no solo un volcado de datos.
- Sentar las bases para la ingesta total del catálogo del competidor en un esquema escalable.

---

## 5. Stakeholders

- **Owner/Analista eCommerce (Fran):** definición de competidores, reglas, consumo de briefs
- **Equipo comercial/marketing:** consumo de insights y alertas
- **Equipo técnico/dev:** mantenimiento de scraping, extracción y jobs
- **Consumidores futuros por API:** Odoo, BI, otras herramientas internas

---

## 6. Definiciones y glosario

- **Competidor:** sitio de eCommerce monitoreado
- **Snapshot:** captura de estado de una página o email en un momento dado
- **Diff:** comparación entre snapshots para detectar cambios
- **Señal comercial:** promo, financiación, envío, banco, urgencia, CTA, campaña
- **Brief diario:** resumen de cambios relevantes detectados en el día
- **Brief semanal:** resumen de tendencias y patrones de la semana
- **Worker:** proceso de background que ejecuta tareas (scraping, parsing, diff, brief)
- **Directus-friendly schema:** esquema SQL diseñado para ser introspectado y operado cómodamente desde Directus

---

## 7. Arquitectura objetivo (alto nivel)

### 7.1 Stack aprobado (MVP)
- **DB principal:** PostgreSQL (fuente de verdad)
- **Panel/backoffice:** Directus (sobre DB existente)
- **Motor/API:** FastAPI
- **Workers:** procesos Python de background (scheduler + tareas)
- **Scraping:** Scrapling / requests + fallback browser automation (si aplica)
- **Parsing emails:** IMAP/Gmail API + parser HTML
- **Formato de entrega:** Markdown + JSON (briefs)

### 7.2 Principio de arquitectura
Separar claramente:

1. **Motor de ingesta y análisis** (FastAPI + workers)
2. **Persistencia e histórico** (PostgreSQL)
3. **Panel de operación** (Directus)
4. **Consumidores externos por API** (Odoo/BI/otras mesas)

### 7.3 Gobernanza del esquema de datos
- El **schema** de PostgreSQL será definido por código/migraciones (Alembic u otro equivalente).
- **Directus** se configurará para **introspectar y operar** sobre el esquema existente.
- Directus **no será** el origen primario del diseño de datos del core.

---

## 8. Requisitos de arquitectura de datos (Directus-friendly)

### 8.1 Convenciones de modelado
El esquema de base deberá seguir estas convenciones:

- Nombres en `snake_case`
- PK simple por tabla (`id` UUID o BIGINT)
- FKs explícitas
- Timestamps estándar: `created_at`, `updated_at`
- Campos de auditoría opcionales: `created_by`, `updated_by`
- `deleted_at` solo en tablas donde tenga sentido soft-delete
- `jsonb` para payloads variables/raw (no como reemplazo de modelado relacional)

### 8.2 Clasificación de tablas para uso en Directus
El modelo deberá separar tablas según propósito operativo:

#### A. Tablas de configuración (editables desde Directus)
- `competitors`
- `monitored_pages`
- `job_configs` (frecuencia, flags)
- `signal_taxonomy`
- `tags` / `competitor_tags`
- `newsletter_accounts` (si aplica y con cuidado de secretos)

#### B. Tablas raw/operativas (lectura o edición restringida)
- `crawl_runs`
- `page_snapshots`
- `newsletter_messages`
- `raw_artifacts`
- `job_execution_logs`

#### C. Tablas de resultados (edición controlada)
- `detected_signals`
- `change_events`
- `daily_briefs`
- `weekly_briefs`

### 8.3 Regla de seguridad operativa en panel
No se deberá permitir edición manual libre sobre tablas raw/logs en Directus para evitar corrupción de histórico.

---

## 9. Compatibilidad futura con índice vectorial (Zvec) — previsto, no MVP

### 9.1 Objetivo futuro
Dejar prevista la posibilidad de añadir un índice vectorial (ej. **Zvec**) para:
- búsqueda semántica en newsletters/snapshots/briefs,
- deduplicación de campañas similares,
- recuperación contextual de eventos históricos.

### 9.2 Principio de diseño
- **PostgreSQL seguirá siendo la DB principal** (fuente de verdad).
- El índice vectorial será un **componente complementario**.
- El core no deberá acoplarse a una implementación vectorial específica.

### 9.3 Preparación mínima en el modelo (sin implementar vectors aún)
Se recomienda dejar previstos campos/estructuras como:
- `content_hash`
- `language`
- `embedding_status` (`pending`, `indexed`, `failed`)
- `embedding_model`
- `embedding_updated_at`

Y/o una cola genérica de indexación semántica:
- `semantic_index_queue` (`entity_type`, `entity_id`, `status`, `attempts`, etc.)

---

## 10. Casos de uso principales

### UC-01 — Monitorear homepage de competidor
**Actor:** Worker de monitoreo web  
**Descripción:** El sistema accede a la homepage del competidor, extrae módulos relevantes (hero, banners, promos, financiación, CTAs) y guarda snapshot + señales detectadas.

### UC-02 — Monitorear páginas promocionales
**Actor:** Worker de monitoreo web  
**Descripción:** El sistema recorre páginas promocionales definidas (`/promociones`, `/ofertas`, `/sale`, etc.) y detecta cambios comerciales.

### UC-03 — Ingestar newsletter
**Actor:** Worker de newsletters  
**Descripción:** El sistema lee emails de casillas suscriptas, parsea HTML, extrae asunto/preheader/CTAs/promos y guarda snapshot + señales.

### UC-04 — Detectar cambios
**Actor:** Worker de diff  
**Descripción:** Compara snapshots previos vs actuales y genera eventos de cambio relevantes.

### UC-05 — Generar brief diario
**Actor:** Worker de briefing  
**Descripción:** Consolida señales y cambios del día, genera resumen estructurado en Markdown/JSON.

### UC-06 — Alerta Inmediata (Slack / Webhook)
**Actor:** Worker de diff / Alertas
**Descripción:** Si un cambio supera un umbral de agresividad (ej. nuevo "50% OFF en toda la tienda"), dispara webhook urgente.

### UC-07 — Revisar datos en panel
**Actor:** Usuario interno  
**Descripción:** Consulta snapshots, alertas y catálogos en Directus.

### UC-08 — Exponer resultados por API
**Actor:** Sistema consumidor externo (futuro: Odoo / BI)  
**Descripción:** Consume briefs, cambios y señales desde endpoints de FastAPI.

### UC-09 — Reutilizar lógica del repo `v0-newsletterAI`
**Actor:** Equipo técnico/dev  
**Descripción:** Encapsular componentes (parsers de IMAP, prompts de IA) del repo legacy.

---

## 11. Requisitos funcionales (RF)

### RF-01 — Gestión de competidores
El sistema debe permitir registrar competidores con al menos:
- nombre
- dominio principal
- país/región
- estado (activo/inactivo)
- prioridad
- tags (ej.: deportes, tecnología, retail)

### RF-02 — Gestión de páginas monitoreadas
El sistema debe permitir asociar a cada competidor una o más páginas monitoreadas:
- homepage
- promos
- financiación
- categorías foco
- otras URLs estratégicas

### RF-03 — Ejecución programada de scraping web
El sistema debe ejecutar tareas programadas de scraping con frecuencia configurable (ej. diario / varias veces por día).

### RF-04 — Captura de snapshots web
Por cada ejecución, el sistema debe almacenar:
- timestamp
- URL
- estado HTTP / resultado
- HTML/raw content (o referencia a storage)
- texto normalizado extraído
- metadata técnica (duración, parser usado, versión de extracción)

### RF-05 — Extracción de señales comerciales web
El sistema debe detectar y normalizar señales como:
- promociones (`% OFF`, `2x1`, combos, etc.)
- financiación (cuotas, banco/tarjeta)
- envío (gratis, umbral)
- urgencia (“último día”, “flash”, etc.)
- CTAs principales
- categorías o marcas destacadas (si detectables)

### RF-06 — Ingesta de newsletters
El sistema debe poder leer emails desde una fuente definida (IMAP o Gmail API) y registrar:
- remitente
- asunto
- fecha/hora
- preheader (si existe)
- cuerpo HTML/raw
- cuerpo texto limpio
- links/CTAs
- imágenes principales (al menos URLs/alt)

### RF-07 — Extracción de señales comerciales de newsletters
El sistema debe detectar en emails las mismas taxonomías base de señales comerciales que en web, para facilitar comparación cross-channel.

### RF-08 — Motor de diff
El sistema debe comparar snapshots consecutivos y generar eventos de cambio clasificables, incluyendo al menos:
- nueva promo detectada
- promo removida
- cambio de financiación
- cambio de banner/hero
- cambio de CTA principal
- nueva comunicación email

### RF-09 — Priorización de cambios
El sistema debe asignar nivel de relevancia (ej. baja/media/alta) a los cambios detectados usando reglas configurables.

### RF-10 — Generación de brief diario
El sistema debe producir un brief diario con:
- resumen ejecutivo (bullets)
- cambios por competidor
- promos/financiación detectadas
- newsletters recibidas
- alertas relevantes
- anexos/referencias (URLs, ids de snapshot)

### RF-11 — Generación de brief semanal
El sistema debe consolidar información de la semana y producir:
- tendencias por competidor
- frecuencia de campañas
- categorías más empujadas
- cambios de financiación
- ranking de intensidad promocional (heurístico)

### RF-12 — Persistencia histórica
El sistema debe conservar histórico de snapshots, señales, cambios y briefs para análisis comparativos futuros.

### RF-13 — Panel operativo en Directus
El sistema debe exponer en Directus (al menos) vistas sobre:
- competidores
- páginas monitoreadas
- snapshots
- newsletters
- cambios detectados
- briefs
- configuraciones/taxonomías

### RF-14 — API de consulta (FastAPI)
El sistema debe ofrecer endpoints para:
- listar briefs
- consultar cambios por fecha/competidor
- consultar señales
- health check
- ejecución manual de jobs (solo admin)

### RF-15 — Reprocesamiento
El sistema debe permitir reprocesar snapshots históricos cuando cambie la lógica de extracción, sin perder el raw original.

### RF-16 — Reutilización de componentes legacy (v0-newsletterAI)
El sistema debe contemplar una etapa de evaluación del repo `v0-newsletterAI` para rescatar componentes reutilizables, priorizando:
- parsers de emails
- normalización
- generación de brief
- conectores de correo

---

## 12. Requisitos no funcionales (RNF)

### RNF-01 — Modularidad
El sistema debe estar diseñado en módulos separados (web monitoring, newsletter monitoring, diff, briefing), para facilitar refactor y reutilización.

### RNF-02 — Migrabilidad por APIs
La lógica core no debe depender del panel (Directus) ni de un consumidor específico (Odoo). Debe poder integrarse con otras mesas/sistemas mediante APIs.

### RNF-03 — Observabilidad mínima
Cada job debe registrar:
- inicio/fin
- duración
- estado (ok/error)
- mensaje de error
- cantidad de objetos procesados

### RNF-04 — Tolerancia a fallas parciales
La falla en un competidor o página no debe detener la ejecución completa del ciclo diario.

### RNF-05 — Auditabilidad
Toda señal y cambio relevante debe ser rastreable al snapshot/email de origen.

### RNF-06 — Performance (MVP)
El sistema debe procesar un conjunto inicial de 5–10 competidores diarios sin intervención manual, en tiempos aceptables para uso interno.

### RNF-07 — Seguridad básica
- credenciales de email y DB en variables de entorno/secret manager
- acceso autenticado a panel y endpoints admin
- no exponer datos sensibles en logs

### RNF-08 — Compatibilidad con Directus
El esquema y operación de datos deben diseñarse para minimizar fricción con introspección, relaciones y uso del panel Directus.

### RNF-09 — Cumplimiento y ética operativa
El scraping debe operar con rate limiting y uso responsable de recursos de sitios de terceros.

---

## 13. Reglas de negocio iniciales (RB)

### RB-01 — Taxonomía unificada de promociones
Toda señal detectada debe mapearse a una taxonomía común (ej. `%OFF`, `CUOTAS`, `ENVIO`, `BANCO`, `COMBO`, `URGENTE`) para comparar entre competidores y canales.

### RB-02 — Snapshot raw obligatorio
No se debe procesar contenido sin guardar raw/artifact o referencia al mismo (HTML/email original).

### RB-03 — “Cambio relevante” > “Cambio técnico”
Cambios puramente técnicos (timestamps, tokens, scripts, hashes) deben excluirse del brief salvo que afecten contenido comercial.

### RB-04 — Canal web y canal email se comparan
Cuando sea posible, el brief debe indicar coherencia o divergencia entre homepage y newsletters.

### RB-05 — Fuente de verdad de schema
La estructura de DB del core se define por migraciones del proyecto; Directus se configura sobre ella.

---

## 14. Modelo conceptual de datos (alto nivel)

### Entidades principales
- **Competitor**
- **MonitoredPage**
- **CrawlRun**
- **PageSnapshot**
- **NewsletterAccount**
- **NewsletterMessage**
- **DetectedSignal** (web/email)
- **ChangeEvent**
- **Product** (Fase 2 ready)
- **PriceHistory** (Fase 2 ready)
- **DailyBrief**
- **WeeklyBrief**
- **JobExecutionLog**
- **RawArtifact**
- **(Futuro) SemanticIndexQueue**

### Relaciones (resumen)
- `Competitor 1..N MonitoredPage`
- `MonitoredPage 1..N PageSnapshot`
- `Competitor 1..N NewsletterMessage` (por mapeo de dominio/remitente o relación configurada)
- `PageSnapshot / NewsletterMessage 1..N DetectedSignal`
- `ChangeEvent` referencia snapshots/mensajes previos/actuales
- `DailyBrief` agrega `ChangeEvent` + `DetectedSignal`
- `WeeklyBrief` agrega `DailyBrief`

---

## 15. Interfaces externas

### 15.1 Sitios web de competidores (entrada)
- HTTP/HTTPS
- HTML server-rendered y/o JS-rendered (con fallback de browser automation)

### 15.2 Casillas de correo / proveedor de email (entrada)
- IMAP o Gmail API (según implementación final)

### 15.3 Directus (panel)
- lectura/escritura sobre tablas seleccionadas de PostgreSQL
- uso como backoffice de operación (no como dueño del core de lógica)

### 15.4 Integración futura con Odoo y otras mesas (salida)
- consumo por API de briefs/alertas/cambios
- no forma parte del MVP, pero queda habilitado por diseño

---

## 16. Requisitos de reporting / briefs

### 16.1 Formato brief diario (mínimo)
- Fecha
- Resumen ejecutivo (3–7 bullets)
- Cambios por competidor
- Promos/financiación destacadas
- Newsletters del día
- Alertas
- Referencias (URLs, snapshots, ids internos)

### 16.2 Formato brief semanal (mínimo)
- Semana analizada
- Cambios relevantes acumulados
- Tendencias por competidor
- Frecuencia de newsletters
- Cambios de financiación
- Categorías/verticales destacadas (si aplica)
- Hipótesis/observaciones (opcional)

### 16.3 Formatos técnicos de salida
- Markdown (`.md`) para lectura humana
- JSON para APIs/integraciones

---

## 17. Requisitos operativos (MVP)

### 17.1 Scheduler
Debe existir un mecanismo para:
- ejecutar monitoreo web (diario o múltiple diario)
- ejecutar ingesta de newsletters
- ejecutar diff
- ejecutar brief diario
- ejecutar brief semanal

### 17.2 Ejecución manual
Debe poder dispararse una corrida manual por:
- competidor
- URL específica
- fecha (reproceso)
- generación manual de brief

### 17.3 Reintentos
Errores transitorios de red deben tener política de reintento configurable.

---

## 18. Supuestos y restricciones

### Supuestos
- Se cuenta con lista inicial de competidores y URLs clave
- Se cuenta con una o más casillas suscriptas a newsletters
- Uso principalmente interno (no SaaS multi-tenant en MVP)

### Restricciones
- El HTML de competidores puede cambiar frecuentemente
- Algunos sitios pueden requerir rendering JS
- Puede haber mecanismos anti-bot (se mitigará de forma responsable)
- No se garantiza stock real en fase 1 (solo señales visibles)

---

## 19. Riesgos principales y mitigaciones

### Riesgo 1 — Cambios de estructura HTML
**Impacto:** rompe extractores  
**Mitigación:** snapshots raw + selectores múltiples + heurísticas por texto + reproceso

### Riesgo 2 — Bloqueos/anti-bot
**Impacto:** fallas de scraping  
**Mitigación:** rate limit, retry controlado, fallback browser, scheduling distribuido

### Riesgo 3 — Falsos positivos en diffs
**Impacto:** ruido en briefs  
**Mitigación:** normalización de contenido, filtros de elementos técnicos, scoring de relevancia

### Riesgo 4 — Sobrecarga operativa
**Impacto:** sistema difícil de mantener  
**Mitigación:** módulos separados, observabilidad, taxonomía común, foco en MVP

### Riesgo 5 — Acoplamiento accidental a Directus
**Impacto:** migraciones futuras difíciles  
**Mitigación:** schema gobernado por código, Directus como panel, API del core independiente

---

## 20. Criterios de aceptación del MVP

El MVP se considera aceptado cuando:

1. Se pueden registrar al menos **5 competidores** con páginas monitoreadas.
2. El sistema ejecuta una corrida diaria automática y guarda snapshots web.
3. El sistema ingesta newsletters desde una casilla definida.
4. El sistema detecta cambios entre corridas (al menos promos/financiación/banner).
5. Se genera un **brief diario en Markdown** con contenido útil por competidor.
6. Los datos se pueden revisar desde **Directus**.
7. Existe **API FastAPI** para consultar briefs/cambios básicos.
8. El sistema conserva histórico y permite reproceso de snapshots.
9. El sistema tolera fallas parciales sin abortar toda la corrida.
10. Se documenta una evaluación inicial del repo `v0-newsletterAI` (qué se reutiliza / qué se descarta).

---

## 21. Roadmap técnico sugerido (referencial)

### Fase 1 — MVP de señales (actual SRS)
- Web monitor + newsletter monitor + diff + brief diario
- PostgreSQL + Directus + FastAPI + workers
- Evaluación y rescate parcial de `v0-newsletterAI`

### Fase 2 — Catálogo profundo
- crawl de categorías/productos
- métricas de SKUs, marcas, verticales
- pricing/stock proxy históricos

### Fase 3 — Inteligencia avanzada
- clasificación semántica
- deduplicación de campañas
- búsqueda semántica sobre histórico (ej. Zvec)
- cruce con datos internos de ventas (Odoo/Magento)

---

## 22. ¿Hace falta PRD además de este SRS?

### Respuesta práctica
Este SRS es **suficiente para empezar a codear el MVP**.

### Recomendación
Crear además un **PRD liviano (1–3 páginas)** para alinear:
- objetivo del MVP
- qué entra / qué no entra
- KPIs de éxito
- prioridades por fase

Esto reduce scope creep y acelera decisiones sin burocracia.

---

## 23. Anexos pendientes (próxima versión)

- A. Taxonomía de promociones/financiación (v1)
- B. Esquema físico inicial de tablas (PostgreSQL + Directus-friendly)
- C. Contrato de API (FastAPI)
- D. Política de scheduling y reintentos
- E. Matriz de evaluación de reutilización del repo `v0-newsletterAI`

