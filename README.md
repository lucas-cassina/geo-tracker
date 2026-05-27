# geo-tracker

Monitorea semanalmente qué tan visible es tu marca en los motores de búsqueda con IA. geo-tracker le hace preguntas a **ChatGPT** y **Google Gemini** y registra si tu marca aparece en las respuestas — el equivalente al SEO tradicional, pero para búsquedas generadas por IA (GEO: Generative Engine Optimization).

## Cómo funciona

Cada lunes a las 9am, el script envía una lista configurable de preguntas a ChatGPT (gpt-4o-search-preview) y Google Gemini (gemini-2.5-flash con Search Grounding). Detecta si alguna respuesta menciona tu marca, guarda los resultados en un JSON y te manda un reporte HTML por email.

El reporte muestra una tabla ✅/❌ por pregunta y motor, la tasa de visibilidad semanal y la variación respecto a la semana anterior.

## Configuración

Todo lo que necesitás personalizar está en **`config.py`**:

**Marca a trackear** — editá `BRAND_KEYWORDS`:

```python
BRAND_KEYWORDS = ["tumarca", "tumarca.com"]
```

**Preguntas** — editá `QUESTIONS`:

```python
QUESTIONS = [
    "¿Qué plataformas existen para X en Argentina?",
    "¿Cuál es la mejor herramienta para Y?",
    "What are the best tools for Z?",  # también funciona en inglés
]
```

Podés mezclar idiomas para cubrir distintas audiencias.

## Requisitos

- Python 3.11+
- API key de [OpenAI](https://platform.openai.com/api-keys) (`sk-proj-...`)
- API key de [Google AI Studio](https://aistudio.google.com/apikey)
- Cuenta de Gmail con [App Password](https://myaccount.google.com/apppasswords) habilitado (requiere 2FA)

## Instalación

```bash
git clone https://github.com/lucas-cassina/geo-tracker.git
cd geo-tracker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Completar .env con las API keys y datos de email
```

### Variables de entorno (`.env`)

```
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AI...

EMAIL_FROM=tu@gmail.com
EMAIL_TO=tu@email.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

Para enviar el reporte a **múltiples destinatarios**, separá las direcciones con coma en `EMAIL_TO`:

```
EMAIL_TO=uno@email.com,dos@email.com,tres@email.com
```

> El App Password de Gmail se genera en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). No es la contraseña normal de la cuenta.

## Uso

### Probar (2 preguntas, sin email)

```bash
source .venv/bin/activate
python3 monitor.py --test
```

### Corrida completa (todas las preguntas + email)

```bash
source .venv/bin/activate
python3 monitor.py
```

Los resultados se guardan en `results/YYYY-MM-DD.json`.

### Activar ejecución semanal automática

```bash
bash setup.sh
```

Registra un cron que corre el monitor cada **lunes a las 9:00 AM**. Para verificar:

```bash
crontab -l | grep geo-tracker
```

## Estructura del proyecto

```
geo-tracker/
├── config.py         # ← Editá aquí: marca a trackear y preguntas
├── monitor.py        # Lógica principal (APIs, detección, email)
├── requirements.txt  # Dependencias Python
├── setup.sh          # Instalación + registro de cron
├── .env.example      # Template de variables de entorno
└── results/          # JSONs con resultados por fecha (auto-generado)
```

## Limitaciones y posibles mejoras

Las respuestas de los modelos de IA son **no determinísticas**: una misma pregunta puede mencionar tu marca un día y no al siguiente, aunque el modelo tenga conocimiento de ella. El tracker mide si tu marca apareció en una respuesta específica en un momento dado — no si "existe" en el índice del motor.

**Falsos negativos** (tu marca existe pero no aparece): ocurren cuando el modelo prioriza otras fuentes, cuando hay noticias recientes de competidores, o cuando la respuesta se trunca y tu marca quedó más abajo en la lista.

**Falsos positivos** (detección incorrecta): poco probables, pero posibles si tu keyword matchea una palabra en otro idioma o contexto, o si Gemini incluye tu URL como fuente sin recomendarla en el texto.

Lo que sí es confiable es la **tendencia a lo largo del tiempo**: si la tasa sube consistentemente de 3/24 a 15/24 semanas seguidas, eso refleja un cambio real en visibilidad.

### Mejoras para reducir el ruido

| Mejora | Cuándo aplicarla | Cómo implementarla |
|---|---|---|
| **Repetir cada pregunta N veces y tomar mayoría** | Si los resultados semanales son muy volátiles | Llamar cada engine 2-3 veces por pregunta y marcar mención solo si aparece en la mayoría |
| **Fijar `temperature=0` en OpenAI** | Para maximizar determinismo en ChatGPT | Agregar `temperature=0` en `query_openai()` en `monitor.py` (Gemini con Search Grounding no lo soporta) |
| **Ampliar el banco de preguntas** | Si querés más robustez estadística | Agregar más preguntas en `config.py`; con 30+ preguntas un falso negativo puntual impacta menos en la tasa |
| **Guardar el texto completo de cada respuesta** | Para auditar manualmente los resultados | Cambiar `response_excerpt` (500 chars) por la respuesta completa en el JSON |

## Costos estimados

| Motor | Costo por corrida | Costo anual |
|---|---|---|
| OpenAI (gpt-4o-search-preview) | ~$0,05 por pregunta (~$0,60 con 12 preguntas) | ~$31 |
| Google Gemini (gemini-2.5-flash) | $0 (tier gratuito) | $0 |
| **Total** | **~$0,60/semana** | **~$31/año** |
