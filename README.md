# Polko AI Visibility Monitor

Agente semanal que consulta los principales motores de búsqueda con IA y registra si **Polko** aparece mencionado en sus respuestas cuando se hacen preguntas sobre el mercado de seguros en Argentina.

## ¿Qué hace?

Cada lunes a las 9am lanza 12 preguntas clave (en español e inglés) a **ChatGPT** y **Google Gemini**, detecta si alguna respuesta menciona a Polko o polko.com.ar, guarda los resultados en un JSON y envía un reporte HTML por email.

Ejemplo de preguntas que se consultan:
- *¿Qué plataformas digitales existen para productores de seguros en Argentina?*
- *¿Cuál es el mejor multicotizador de seguros para productores en Argentina?*
- *What are the best InsurTech platforms for insurance producers in Argentina?*

El reporte muestra una tabla con ✅/❌ por pregunta y motor, la tasa de visibilidad semanal y la variación respecto a la semana anterior.

## Requisitos

- Python 3.11+
- API key de [OpenAI](https://platform.openai.com/api-keys) (`sk-proj-...`)
- API key de [Google AI Studio](https://aistudio.google.com/apikey) (funciona con cuenta @polko.com.ar)
- Gmail con [App Password](https://myaccount.google.com/apppasswords) habilitado (requiere 2FA activo)

## Instalación

```bash
git clone <repo>
cd geo-tracker

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con las API keys
```

### Variables de entorno (`.env`)

```
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AI...

EMAIL_FROM=tu@email.com
EMAIL_TO=tu@email.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> La App Password de Gmail se genera en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). No es la contraseña normal de la cuenta.

## Uso

### Probar sin enviar email (2 preguntas)

```bash
source .venv/bin/activate
python3 monitor.py --test
```

### Correr completo (12 preguntas + email)

```bash
source .venv/bin/activate
python3 monitor.py
```

Los resultados se guardan en `results/YYYY-MM-DD.json`.

### Activar ejecución semanal automática

```bash
bash setup.sh
```

Registra un cron que corre el monitor cada **lunes a las 9:00 AM** y guarda el log en `results/cron.log`.

Para verificar que quedó registrado:

```bash
crontab -l | grep polko
```

## Estructura del proyecto

```
geo-tracker/
├── monitor.py        # Script principal
├── requirements.txt  # Dependencias Python
├── setup.sh          # Instalación + registro de cron
├── .env.example      # Template de variables de entorno
└── results/          # JSONs con resultados por fecha (auto-generado)
```

## Costos estimados

| Motor | Costo por corrida | Costo anual |
|---|---|---|
| OpenAI (gpt-4o-search-preview) | ~$0,31 | ~$16 |
| Google Gemini (gemini-2.5-flash) | $0 (tier gratuito) | $0 |
| **Total** | **~$0,31/semana** | **~$16/año** |
