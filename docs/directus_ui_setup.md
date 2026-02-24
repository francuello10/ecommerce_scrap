# Directus UI Configuration Guide (Ready for Simulation)

Para que mañana puedas ver los datos como un pro, seguí esta guía de configuración en el panel de Directus (`localhost:8055`).

## 1. Agrupamiento de Colecciones
Andá a *Settings > Data Model* y creá carpetas para agrupar:

| Grupo | Colecciones | Icono |
|:---|:---|:---|
| **Intelligence Center** | `daily_brief`, `weekly_brief`, `change_event`, `detected_signal` | `insights` |
| **Operations** | `competitor`, `monitored_page`, `newsletter_account`, `newsletter_subscription` | `settings_input_component` |
| **SaaS & Clients** | `client`, `subscription_tier`, `upsell_event`, `industry` | `business` |
| **Raw Logs** | `page_snapshot`, `newsletter_message`, `job_execution_log`, `crawl_run` | `history` |

## 2. Configuración de Interfaces (UX)

### Ver Mails Crudos (`newsletter_message`)
- **Campo `body_html`**: Cambiar Interface a "Markdown" o "Codemirror" (Language: HTML).
- **Campo `body_preview`**: Interface "Textarea".

### Ver Capturas de Pantalla (`page_snapshot`)
- **Campo `screenshot_url`**: 
    - Interface: "Image".
    - Display: "Image" (con preview en la lista).

### Briefings (`daily_brief`)
- **Campo `content_markdown`**: Interface "WYSIWYG" o "Markdown".
- **Campo `content_json`**: Interface "Codemirror" (Language: JSON).

### Alertas y Semáforos (`change_event`)
- **Campo `severity`**: 
    - Display: "Labels".
    - Colores: `CRITICAL` -> Rojo, `HIGH` -> Naranja, `MEDIUM` -> Amarillo, `LOW` -> Azul.

## 3. Vistas Recomendadas
- **Daily Intelligence**: Creada sobre `daily_brief` filtrando por hoy.
- **Top Competitor Moves**: Creada sobre `change_event` ordenado por `severity` desc.
