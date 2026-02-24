# Strategic Flows: Economic & Operational Vision

Estos diagramas representan cómo el sistema captura valor y cómo interactúan los distintos perfiles con la plataforma.

## 1. El Flujo del Cliente (Valor de Negocio)
Cómo un CMO o Gerente de eCommerce usa la herramienta para ganar mercado.

```mermaid
graph TD
    A["Monitorización Continua (Web + Email)"] --> B{"Interferencia Detectada"}
    B -- "Cambio Agresivo (30% OFF)" --> C["Alerta Slack CRITICAL"]
    B -- "Promo Estándar" --> D["Briefing Diario IA"]
    
    C --> E["Acción Inmediata Marketing"]
    D --> F["Ajuste Estratégico Semanal"]
    
    E --> G["ROI: Protección de Conversión"]
    F --> G
```

## 2. El Flujo del Owner (SaaS Operations)
Cómo gestionas el negocio y escalas la plataforma.

```mermaid
graph LR
    A["Directus Dashboard"] --> B["Onboarding: Client + Industry"]
    B --> C["Suggestion Engine"]
    C --> D["Auto-Config Monitoring"]
    
    D --> E["Workers (24/7 Monitoring)"]
    E --> F["Upsell Engine: Historical Data Alert"]
    
    F --> G["Monetización / Tier Upgrade"]
```

## 3. Arquitectura de Datos (CTO View)
Estructura de "Raw to Brief" para asegurar trazabilidad.

```mermaid
sequenceDiagram
    participant W as Worker (HTTPX/PW)
    participant DB as PostgreSQL (Raw)
    participant D as Diff Engine
    participant LLM as AI Briefing Engine
    participant U as User (Directus)

    W->>DB: Save Snapshot & Newsletter
    DB->>D: Analyze Signals (Taxonomy)
    D->>DB: Save Change Events
    DB->>LLM: Fetch daily changes
    LLM->>DB: Save Executive Brief (MD/JSON)
    U->>DB: Inspect Signals & Brief
```
