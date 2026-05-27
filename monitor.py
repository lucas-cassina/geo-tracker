#!/usr/bin/env python3
"""
geo-tracker — Monitor de Visibilidad en Motores de Búsqueda con IA
Detecta semanalmente si tu marca aparece en respuestas de ChatGPT y Google Gemini.
"""

import email.utils
import json
import os
import re
import smtplib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from config import BRAND_KEYWORDS, QUESTIONS

load_dotenv()


# ---------------------------------------------------------------------------
# Detección de menciones
# ---------------------------------------------------------------------------

def check_mention(text: str, sources: list[str] | None = None) -> dict:
    """Retorna si alguna keyword de la marca aparece en el texto o en las fuentes."""
    text_lower = text.lower() if text else ""
    mentioned_in_text = any(kw in text_lower for kw in BRAND_KEYWORDS)

    mentioned_in_sources = False
    if sources:
        mentioned_in_sources = any(
            any(kw in src.lower() for kw in BRAND_KEYWORDS) for src in sources
        )

    mentioned = mentioned_in_text or mentioned_in_sources

    context = None
    if mentioned_in_text and text:
        # Extraer fragmento de contexto (±150 chars alrededor de la primera mención)
        idx = next(
            (text_lower.index(kw) for kw in BRAND_KEYWORDS if kw in text_lower), None
        )
        if idx is not None:
            start = max(0, idx - 150)
            end = min(len(text), idx + 150)
            context = "..." + text[start:end].strip() + "..."

    return {
        "mentioned": mentioned,
        "in_text": mentioned_in_text,
        "in_sources": mentioned_in_sources,
        "context": context,
    }


# ---------------------------------------------------------------------------
# Clientes de API
# ---------------------------------------------------------------------------

def query_openai(question: str) -> dict:
    """Consulta ChatGPT con búsqueda web (gpt-4o-search-preview)."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY no configurada", "mentioned": False}

    try:
        client = openai.OpenAI(api_key=api_key)
        # gpt-4o-search-preview no acepta role "system" ni max_tokens
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Busca información actualizada en internet y responde con detalle, "
                        "mencionando plataformas y herramientas concretas disponibles hoy. "
                        f"Pregunta: {question}"
                    ),
                }
            ],
        )
        text = response.choices[0].message.content or ""
        result = check_mention(text)
        result["response_excerpt"] = text[:500]
        return result
    except Exception as exc:
        return {"error": str(exc), "mentioned": False}


def query_gemini(question: str) -> dict:
    """Consulta Google Gemini con Search Grounding."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY no configurada", "mentioned": False}

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            "Busca información actualizada en internet y responde con detalle, "
            "mencionando plataformas y herramientas concretas disponibles hoy. "
            f"Pregunta: {question}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        # response.text lanza ValueError en respuestas bloqueadas por safety filters
        try:
            text = response.text or ""
        except ValueError:
            text = ""

        # Extraer URLs de grounding metadata
        sources = []
        try:
            for candidate in response.candidates:
                gm = getattr(candidate, "grounding_metadata", None)
                if gm:
                    for chunk in getattr(gm, "grounding_chunks", []):
                        web = getattr(chunk, "web", None)
                        if web and getattr(web, "uri", None):
                            sources.append(web.uri)
        except Exception:
            pass

        result = check_mention(text, sources)
        result["response_excerpt"] = text[:500]
        result["sources"] = sources[:5]
        return result
    except Exception as exc:
        return {"error": str(exc), "mentioned": False}


# ---------------------------------------------------------------------------
# Orquestación principal
# ---------------------------------------------------------------------------

ENGINE_RUNNERS = {
    "openai": query_openai,
    "gemini": query_gemini,
}


def _run_question(question: str) -> dict:
    """Ejecuta todos los motores para una pregunta en paralelo."""
    engines_result = {}
    with ThreadPoolExecutor(max_workers=len(ENGINE_RUNNERS)) as pool:
        futures = {
            pool.submit(runner, question): name
            for name, runner in ENGINE_RUNNERS.items()
        }
        for future in as_completed(futures):
            engines_result[futures[future]] = future.result()
    return {"question": question, "engines": engines_result}


def run_monitoring(questions: list[str], verbose: bool = False) -> dict:
    """Ejecuta todas las consultas en paralelo y retorna el resultado completo."""
    today = date.today().isoformat()

    if verbose:
        print(f"   Ejecutando {len(questions)} preguntas × {len(ENGINE_RUNNERS)} motores en paralelo...")

    results = []
    with ThreadPoolExecutor(max_workers=len(questions)) as pool:
        futures = {pool.submit(_run_question, q): q for q in questions}
        for future in as_completed(futures):
            item = future.result()
            results.append(item)
            if verbose:
                q_short = item["question"][:70]
                for engine, res in item["engines"].items():
                    if res.get("mentioned"):
                        print(f"  ✅ [{engine}] {q_short}...")
                    elif res.get("error"):
                        print(f"  ⚠️  [{engine}] Error: {res['error'][:60]}")
                    else:
                        print(f"  ❌ [{engine}] {q_short}...")

    # Restaurar el orden original de QUESTIONS para consistencia en el reporte
    order = {q: i for i, q in enumerate(questions)}
    results.sort(key=lambda r: order.get(r["question"], 999))

    total = sum(len(r["engines"]) for r in results)
    mentioned_count = sum(
        1 for r in results for res in r["engines"].values() if res.get("mentioned")
    )
    rate = f"{mentioned_count / total * 100:.1f}%" if total > 0 else "0%"

    return {
        "date": today,
        "summary": {
            "total_queries": total,
            "polko_mentioned": mentioned_count,
            "mention_rate": rate,
        },
        "results": results,
    }


def save_results(data: dict) -> Path:
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    base = results_dir / f"{data['date']}.json"
    # No sobreescribir si ya existe (ej: segunda corrida el mismo día)
    path = base
    counter = 2
    while path.exists():
        path = results_dir / f"{data['date']}_{counter}.json"
        counter += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def load_previous_results() -> dict | None:
    """Carga el resultado más reciente con al menos 6 días de antigüedad (semana anterior)."""
    results_dir = Path(__file__).parent / "results"
    cutoff = date.today() - timedelta(days=6)
    files = sorted(results_dir.glob("*.json"), reverse=True)
    for f in files:
        try:
            file_date = date.fromisoformat(f.stem[:10])
        except ValueError:
            continue
        if file_date <= cutoff:
            try:
                return json.loads(f.read_text())
            except Exception:
                continue
    return None


# ---------------------------------------------------------------------------
# Reporte HTML por email
# ---------------------------------------------------------------------------

CELL_NO = '<td style="background:#f8d7da;color:#721c24;text-align:center;padding:8px 10px;">❌</td>'
CELL_ERR = '<td style="background:#fff3cd;color:#856404;text-align:center;padding:8px 10px;">⚠️</td>'

ENGINE_LABELS = {"openai": "ChatGPT", "gemini": "Gemini"}


def _cell_yes(context: str | None) -> str:
    inner = '<div style="font-size:20px;">✅</div>'
    if context:
        ctx_escaped = context.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        inner += f'<div style="font-size:11px;color:#155724;margin-top:4px;font-style:italic;line-height:1.4;">{ctx_escaped}</div>'
    return f'<td style="background:#d4edda;padding:8px 10px;vertical-align:top;">{inner}</td>'


def build_html_report(data: dict, previous: dict | None) -> str:
    summary = data["summary"]
    prev_rate = previous["summary"]["mention_rate"] if previous else None
    trend = ""
    if prev_rate is not None:
        prev_val = float(prev_rate.replace("%", ""))
        curr_val = float(summary["mention_rate"].replace("%", ""))
        diff = curr_val - prev_val
        trend = f" ({'▲' if diff >= 0 else '▼'} {abs(diff):.1f}% vs semana anterior)"

    rows = ""
    for item in data["results"]:
        q = item["question"]
        cells = ""
        for engine in ENGINE_LABELS:
            res = item["engines"].get(engine, {})
            if res.get("error"):
                cell = CELL_ERR
            elif res.get("mentioned"):
                cell = _cell_yes(res.get("context"))
            else:
                cell = CELL_NO
            cells += cell
        rows += f"<tr><td style='padding:8px 10px;font-size:13px;vertical-align:top;'>{q}</td>{cells}</tr>"

    engine_headers = "".join(
        f'<th style="width:20%;text-align:center;padding:8px 12px;">{lbl}</th>'
        for lbl in ENGINE_LABELS.values()
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:860px;margin:40px auto;">
  <h1 style="color:#1a1a2e;">geo-tracker — Monitor de Visibilidad en IA</h1>
  <p style="color:#666;margin-top:-12px;">Reporte del {data['date']}</p>

  <table style="border-collapse:collapse;margin-bottom:24px;">
    <tr>
      <td style="background:#f0f4ff;border-radius:8px;padding:12px 28px;text-align:center;margin-right:12px;">
        <div style="font-size:28px;font-weight:bold;color:#16213e;">{summary['mention_rate']}</div>
        <div style="font-size:12px;color:#666;">Tasa de visibilidad{trend}</div>
      </td>
      <td style="width:16px;"></td>
      <td style="background:#f0f4ff;border-radius:8px;padding:12px 28px;text-align:center;">
        <div style="font-size:28px;font-weight:bold;color:#16213e;">{summary['polko_mentioned']}/{summary['total_queries']}</div>
        <div style="font-size:12px;color:#666;">Consultas con mención</div>
      </td>
    </tr>
  </table>

  <h2 style="color:#16213e;">Detalle por pregunta y motor</h2>
  <table style="border-collapse:collapse;width:100%;margin-top:8px;">
    <thead>
      <tr style="background:#16213e;color:white;">
        <th style="text-align:left;padding:8px 12px;">Pregunta</th>
        {engine_headers}
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <p style="color:#aaa;font-size:11px;margin-top:28px;">Generado por geo-tracker</p>
</body>
</html>"""


def _parse_recipients(value: str) -> list[str]:
    """Parsea EMAIL_TO soportando múltiples destinatarios y display names con comas."""
    return [addr for _, addr in email.utils.getaddresses([value]) if addr]


def send_email_report(data: dict, previous: dict | None) -> None:
    email_from = os.environ.get("EMAIL_FROM", "")
    email_to = os.environ.get("EMAIL_TO", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not all([email_from, email_to, password]):
        print("⚠️  Variables de email incompletas — omitiendo envío.")
        return

    html = build_html_report(data, previous)
    summary = data["summary"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"geo-tracker — {data['date']} — "
        f"{summary['polko_mentioned']}/{summary['total_queries']} menciones ({summary['mention_rate']})"
    )
    msg["From"] = email_from
    msg["To"] = email_to
    msg.attach(MIMEText(html, "html", "utf-8"))

    # Extraer dirección bare para login (soporta display names)
    _, login_address = email.utils.parseaddr(email_from)
    recipients = _parse_recipients(email_to)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(login_address, password)
            server.sendmail(login_address, recipients, msg.as_string())
        print(f"✉️  Reporte enviado a {email_to}")
    except smtplib.SMTPAuthenticationError:
        print("⚠️  Error de autenticación SMTP — verificá el Gmail App Password en .env")
    except smtplib.SMTPException as exc:
        print(f"⚠️  Error al enviar email: {exc}")
    except OSError as exc:
        print(f"⚠️  Error de red al conectar con Gmail: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    test_mode = "--test" in sys.argv
    questions = QUESTIONS[:2] if test_mode else QUESTIONS

    if test_mode:
        print("🧪 Modo test — usando 2 preguntas, sin enviar email.")

    print(f"🔍 geo-tracker — {date.today().isoformat()}")
    print(f"   Preguntas: {len(questions)} | Motores: {len(ENGINE_RUNNERS)}")

    data = run_monitoring(questions, verbose=True)
    path = save_results(data)
    print(f"\n💾 Resultados guardados en: {path}")

    s = data["summary"]
    print(f"📊 Resumen: {s['polko_mentioned']}/{s['total_queries']} menciones ({s['mention_rate']})")

    if not test_mode:
        previous = load_previous_results()
        send_email_report(data, previous)


if __name__ == "__main__":
    main()
