# Plan de Rescate: `v0-newsletterAI`

## 1. Diagnóstico del Repositorio Legacy
- **Stack viejo:** Next.js (TypeScript), Node.js, Prisma ORM, ImapFlow.
- **Stack nuevo:** FastAPI (Python), PostgreSQL + Alembic, Directus.

Dado el cambio de lenguaje (TS a Python) y de ORM (Prisma a SQLAlchemy/SQLModel), **no realizaremos un "copiar y pegar" directo**. En lugar de eso, realizaremos una portabilidad de *know-how* y reglas de negocio.

## 2. Componentes a Rescatar Categóricamente
1. **Lógica de Conexión y Lectura IMAP**
   - *Dónde está:* `v0-newsletterAI/workers/email-processor-v2.ts`
   - *Qué rescatamos:* La estrategia para buscar mails, lidiar con "multipart" (texto plano vs HTML) e identificar links clave. Se re-implementará usando librerías de Python como `imap-tools`.

2. **Ingeniería de Prompts y Extracción con IA**
   - *Dónde está:* Posiblemente en el processor o utilidades asociadas a `@google/generative-ai`.
   - *Qué rescatamos:* Los prompts exactos. Saber qué se le pedía al LLM (ej. extrae precio, promoción, urgencia) es sumamente valioso. En Python usaremos llamadas estructuradas a LLMs (ej. con Pydantic) para forzar un output JSON predecible.

3. **Heurísticas de Limpieza**
   - *Qué rescatamos:* Cualquier regex o regla usada para limpiar HTML sucio antes de procesar, eliminando ruido técnico.

4. **Modelos de Datos como Inspiración**
   - *Qué rescatamos:* Revisar el esquema viejo (en `v0-newsletterAI/prisma/`) ayuda a no olvidar campos útiles al armar el nuevo modelo *Directus-friendly* en PostgreSQL.

## 3. Componentes que se Descartan
- La Interfaz de Usuario de Next.js. El rol de Backoffice lo asume **Directus**.
- El motor de background en TS. El orquestamiento quedará en Python.
