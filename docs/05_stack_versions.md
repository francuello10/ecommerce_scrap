# Definición de Stack Tecnológico y Versiones (Q1 2026)

Para garantizar un balance óptimo entre **software novedoso (moderno)** y **alta estabilidad (production-ready)**, detallamos a continuación las herramientas y versiones recomendadas para la construcción del MVP.

---

## 1. Core de Lenguaje y Entorno

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **Python** | `3.12.x` | Ofrece mejoras masivas de rendimiento y mensajería de error sobre 3.11. Aunque 3.13 ya existe, la 3.12 tiene un ecosistema 100% maduro y todas las librerías de IA/Scraping la soportan sin fricción. |
| **Gestor de Paquetes** | `uv` (Astral) | Reemplazo moderno y extremadamente rápido (escrito en Rust) para `pip` y `poetry`. Es el estándar de facto actual para proyectos Python eficientes. |

---

## 2. Base de Datos y Panel (Backoffice)

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **PostgreSQL** | `16.x` | Extremadamente estable. Soporte nativo y optimizado para JSONB (vital para guardar _snapshots_) y excelente rendimiento. La v17 es muy nueva; la 16 garantiza paz mental y soporta pgvector sin problemas si se requiere a futuro. |
| **Directus** | `11.x` (o latest `10.13+`) | La plataforma Node+Vue ideal como un BaaS headless. Su última versión mejora la introspección de esquemas y el manejo de flujos, respetando las PKs y FKs que definamos en Postgres. |

---

## 3. Backend, API y ORM

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **FastAPI** | `0.115.+` / `0.116+` | Estándar dorado para APIs asíncronas en Python. Usaremos las nuevas sintaxis orientadas a dependencias de tipado (`Annotated`). |
| **Pydantic** | `2.9.+` | El núcleo de validación de datos en FastAPI (v2 reescrito en Rust, 5x-50x más rápido). |
| **SQLAlchemy** | `2.0.+` | Usaremos la API 2.0 (estricta) asíncrona (`asyncpg`). El modelo declarativo es robusto, tipado y nos permite crear el modelo *Directus-friendly* desde código. |
| **Alembic** | `1.13.+` | El motor de migraciones por defecto para SQLAlchemy. |
| **asyncpg** | `0.30.+` | El driver asíncrono para PostgreSQL más rápido en ecosistema Python. |

---

## 4. Workers y Procesamiento de Background

Para las tareas automatizadas (Scraping, IMAP, Briefs) necesitamos un orquestador. Ya no recomendamos *Celery* por su complejidad para proyectos modernos; en su lugar:

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **ARQ** (Async Redis Queue) | `0.26.+` | Un sistema de colas de trabajos en background rápido, moderno e integrado 100% con `asyncio` nativo. Ideal para workers en FastAPI. Requiere Redis básico. |
| **Redis** | `7.2.+` | El broker de mensajes súper estable y ligero para que opere ARQ. |

---

## 5. Módulo de Scraping y Diffing

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **HTTPX** | `0.28.+` | El reemplazo moderno y asíncrono de la famosa librería `requests`. Vital para descargar el HTML de múltiples competidores en paralelo. |
| **Playwright** | `1.49.+` | Para el scraping de páginas complejas en React/Vue que requieran abrir un "Navegador Headless" y renderizar el JS. Mucho más moderno y estable que Selenium. |
| **Scrapling** | `0.2.+` | Si mencionaste Scrapling en el SRS, es una opción rápida y nueva. Pero *BeautifulSoup4* (4.12+) sigue siendo el salvoconducto confiable para el diffing de HTML. |
| **DeepDiff** | `8.0.+` | (Opcional) Librería para comparar y generar diffs de estructuras de datos (JSONs o diccionarios derivados de HTML parseado). |

---

## 6. Módulo de E-mails (Newsletter Monitor)

| Tecnología / Herramienta | Versión Recomendada | Justificación |
| :--- | :--- | :--- |
| **imap-tools** | `1.7.+` | Muchísimo más pythónico y fácil de usar que el módulo `imaplib` que trae Python por defecto. Aunque es sincrónico, se porta perfecto en workers separados usando threads o wrappers asíncronos. |
| **beautifulsoup4** | `4.12.+` | Indispensable para limpiar la "basura" del tipico HTML de Mailchimp/Klaviyo en los newsletters, antes de mandar el texto limpio a analizar (o al LLM). |

---

## Resumen de Integración (La "Golden Stack" 2026)

Tu `pyproject.toml` (o `requirements.txt` manejado por `uv`) base se vería algo así:

```toml
[project]
name = "competitive-intelligence-engine"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.13.3",
    "pydantic>=2.9.2",
    "pydantic-settings>=2.6.0",
    "arq>=0.26.1",
    "httpx>=0.28.0",
    "playwright>=1.49.0",
    "beautifulsoup4>=4.13.3",
    "imap-tools>=1.7.1",
    "wappalyzer-next>=0.1.0",
]
```

### ¿Por qué esta selección?
Es el **sweet-spot** entre:
1. **Desempeño y Escalabilidad:** Todo es asíncrono desde la DB (`asyncpg`), la API (`FastAPI`) hasta la obtención de datos web (`HTTPX`).
2. **Modernidad (State-of-the-Art):** `uv`, pydantic v2, y SQLAlchemy 2.0 son las herramientas con mayor financiamiento y adopción masiva en este momento.
3. **Mantenibilidad:** Tipado estricto extremo con Python 3.12 y Pydantic reduce la fragilidad que tenías en Javascript/Node sin strict mode.
