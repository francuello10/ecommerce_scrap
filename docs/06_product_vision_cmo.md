# Visión de Producto y Estrategia Competitiva (Perspectiva CMO)

*Documento estratégico para guiar el desarrollo técnico desde la visión de negocio.*

## 1. El Problema Base (Por qué construimos esto)
Como CMO de un retail deportivo (Nike, Adidas, Puma) o de tecnología (Lenovo, Asus), mi problema no es la falta de datos, es el **exceso de ruido y el delay en la reacción**. 

Cuando mi competidor directo lanza un "Special Sale 40% OFF en Running" o suma "12 cuotas sin interés con Banco Nación", **cada hora que tardo en darme cuenta y reaccionar, pierdo cuota de mercado (Share of Wallet)**. 

No me sirve un reporte el lunes siguiente. Necesito **Inteligencia Accionable Casi en Tiempo Real**.

## 2. Lo que nos estaba faltando en el MVP original (Los puntos ciegos)

### A. Entender el "Ecosistema de Plataformas"
Nuestros competidores no usan webs caseras. Usan **VTEX (IO / Legacy), Magento 2, Shopify Plus, Tiendanube o WooCommerce**. 
**Visión Técnica:** En lugar de hacer selectores XPath genéricos que se rompen, debemos **"olfatear"** la plataforma subyacente. 
- Si es VTEX IO, buscamos el payload JSON de `__STATE__`.
- Si es Shopify, buscamos el `window.Shopify`. 
- Esto hace que el scraper sea 10x más robusto.

### B. Mapeo de Catálogo (El elefante en la habitación)
El MVP actual vigila "la vidriera" (Homepage, Newsletters). Pero el negocio pasa adentro.
*¿Qué pasa si el competidor no anuncia la promo en la home, pero bajó un 15% todos los botines Adidas?*
**Ajuste:** Debemos preparar la arquitectura en la Fase 1 para la ingesta masiva de catálogos (Fase 2). Esto implica que nuestra base de datos debe soportar millones de registros (SKUs, Historial de Precios, Stock Flags) sin que el panel de Directus colapse.

### C. La "Agresividad" y "Profundidad" Promocional
Saber que hay "30% OFF en Zapatillas" es el nivel 1.
El nivel 2 (CMO view) es saber **qué tan profundo es el descuento y sobre qué volumen del catálogo aplica**.
**Ajuste:** Nuestro scraper de páginas promocionales no solo debe capturar el banner, debe intentar contar (paginar) cuántos SKUs están afectados por esa promoción específica.

### D. El Historial Oculto ("Shadow Pricing")
Los eCommerces juegan con el "precio de lista" vs "precio final". A veces suben el precio de lista un jueves para mostrar un "falso descuento" el viernes (Viernes Negro/Hot Sale).
**Ajuste:** Para el roadmap futuro, el trackeo de precios debe registrar siempre Precio Lista, Precio Oferta y el Beneficio Financiero (cuotas).

### E. Entender los Canales Ocultos
Las promociones más agresivas a veces no están en la home ni en el newsletter. Están en:
1. Push Notifications de las Apps móvies. (Fuera de MVP, pero a tener en radar).
2. Segmentación de Mailing (Solo le llega el 40% a clientes VIP). (Nuestro mailer debe ser un perfil "enriquecido" y "recurrente").

---

## 3. Requerimientos Inmediatos a sumar al Core (Para el Equipo Técnico)

A partir de esta visión, ordeno al equipo técnico realizar los siguientes ajustes al diseño base:

1. **Pluggable Extractors por Plataforma:** El motor de scraping web (`monitored_page`) debe tener "Adapters" o estrategias por e-commerce engine. Que el bot detecte si la URL es Vtex o Shopify y use el parser que mejor se adapte (ej. leer JSON objects vs scrapear HTML crudo).
2. **Modelo de Datos Extensible:** La base de datos debe contemplar ya las tablas `Product` y `PriceHistory` aunque en el MVP solo las poblemos con algunos productos destacados de la home. No quiero que haya que refactorizar todo en la Fase 2.
3. **Métricas de Impacto en el Brief:** El brief no puede ser solo descriptivo ("Pusieron un banner"). Tiene que tener semántica: "Cambio de Hero Banner: Pasaron de foco 'Lifestyle' a foco 'Liquidación/Sale'". 
4. **Alertas Push/Urgentes:** El brief diario está bien para planificar. Pero si detectamos una campaña "Flash Sale Solo por Hoy" a las 9:00 AM, necesito una **Alerta Inmediata** (webhook a Slack/Discord), no un resumen al final del día.

---

## 4. Evolución: Del MVP al Deluxe 💎 (Actualizado 2026-02-24)

Hemos superado el "ruido operacional" inicial implementando las fases 8 y 9:
- **Catálogo Profundo (Fase 8)**: Ya no solo miramos la home; extraemos descripciones de producto, galerías de imágenes full y jerarquías de categorías.
- **Inteligencia de Conversión (Fase 9)**: Capturamos social proof (ratings, reviews) y triggers de urgencia (badges) para entender la psicología de venta del rival.

El Engine es ahora una herramienta de **Benchmarking Premium**.
