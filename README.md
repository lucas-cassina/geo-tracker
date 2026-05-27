# geo-tracker

Track how visible your brand is in AI-powered search engines. geo-tracker queries ChatGPT and Google Gemini weekly with a custom list of questions and records whether your brand appears in the responses — the equivalent of SEO rank tracking, but for Generative Engine Optimization (GEO).

## How it works

Every Monday at 9am, the script sends a configurable list of questions to **ChatGPT** (gpt-4o-search-preview) and **Google Gemini** (gemini-2.5-flash with Search Grounding). It checks each response for mentions of your brand name or domain, saves the results as JSON, and emails you an HTML report.

The report shows a ✅/❌ table per question and engine, a weekly visibility rate, and the trend vs. the previous week.

## Customization

**Changing the brand to track** — edit the `BRAND_KEYWORDS` list in `monitor.py`:

```python
BRAND_KEYWORDS = ["yourbrand", "yourbrand.com"]
```

**Changing the questions** — edit the `QUESTIONS` list in `monitor.py`:

```python
QUESTIONS = [
    "What are the best tools for X in Y?",
    "Which platforms do professionals use for Z?",
    ...
]
```

Questions can be in any language. Mix languages to cover different search audiences.

## Requirements

- Python 3.11+
- [OpenAI API key](https://platform.openai.com/api-keys) (`sk-proj-...`)
- [Google AI Studio API key](https://aistudio.google.com/apikey)
- Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled (requires 2FA)

## Installation

```bash
git clone https://github.com/lucas-cassina/geo-tracker.git
cd geo-tracker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your API keys and email in .env
```

### Environment variables (`.env`)

```
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AI...

EMAIL_FROM=you@gmail.com
EMAIL_TO=you@email.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> Gmail App Passwords are generated at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). This is not your regular Gmail password.

## Usage

### Test run (2 questions, no email)

```bash
source .venv/bin/activate
python3 monitor.py --test
```

### Full run (all questions + email report)

```bash
source .venv/bin/activate
python3 monitor.py
```

Results are saved to `results/YYYY-MM-DD.json`.

### Schedule weekly runs (every Monday at 9am)

```bash
bash setup.sh
```

This installs dependencies and registers a cron job. To verify it's active:

```bash
crontab -l | grep geo-tracker
```

## Project structure

```
geo-tracker/
├── monitor.py        # Main script — edit QUESTIONS and BRAND_KEYWORDS here
├── requirements.txt  # Python dependencies
├── setup.sh          # Install + register cron job
├── .env.example      # Environment variable template
└── results/          # Weekly JSON results (auto-created)
```

## Estimated costs

| Engine | Cost per run | Cost per year |
|---|---|---|
| OpenAI (gpt-4o-search-preview) | ~$0.31 | ~$16 |
| Google Gemini (gemini-2.5-flash) | $0 (free tier) | $0 |
| **Total** | **~$0.31/week** | **~$16/year** |
