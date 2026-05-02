#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")
NEWS_PER_REGION = 6

REGIONS = ["Internacional", "USA", "Europa", "Argentina"]
TOPICS = [
    "política",
    "economía",
    "tecnología",
    "IA",
    "fintech",
    "criptomonedas",
    "startups",
    "ciencia",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Daily Brief</title>
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif;
        background-color: #f8fafc;
        color: #1e293b;
        line-height: 1.6;
      }
      .wrapper {
        background-color: #f8fafc;
        padding: 24px 16px 48px;
      }
      .container {
        max-width: 680px;
        margin: 0 auto;
      }
      .header {
        background: #0f172a;
        border-radius: 16px;
        padding: 52px 40px 44px;
        text-align: center;
        margin-bottom: 8px;
        overflow: hidden;
      }
      .header-eyebrow {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 4px;
        color: #60a5fa;
        margin-bottom: 16px;
      }
      .header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.5px;
        line-height: 1.25;
        margin-bottom: 12px;
      }
      .header h1 .name {
        color: #93c5fd;
      }
      .header .subtitle {
        font-size: 0.9rem;
        color: #94a3b8;
        line-height: 1.6;
      }
      .section {
        margin-top: 36px;
      }
      .section-label {
        display: block;
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 3px;
        color: #64748b;
        margin-bottom: 6px;
      }
      .section-divider {
        height: 2px;
        background: linear-gradient(to right, #3b82f6 0%, transparent 70%);
        border-radius: 1px;
        margin-bottom: 16px;
      }
      .news-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      .card-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 8px;
      }
      .tag {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 4px 10px;
        border-radius: 20px;
        background: #eff6ff;
        color: #1d4ed8;
      }
      .news-date {
        font-size: 0.78rem;
        color: #94a3b8;
      }
      .news-card h3 {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.4;
        margin-bottom: 10px;
      }
      .news-card p {
        font-size: 0.92rem;
        color: #475569;
        line-height: 1.75;
        margin-bottom: 16px;
      }
      .card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-top: 1px solid #f1f5f9;
        padding-top: 14px;
        flex-wrap: wrap;
        gap: 8px;
      }
      .news-source {
        font-size: 0.8rem;
        color: #94a3b8;
      }
      .news-source a {
        color: #64748b;
        text-decoration: none;
        font-weight: 600;
      }
      .read-more {
        font-size: 0.82rem;
        font-weight: 600;
        color: #2563eb;
        text-decoration: none;
        white-space: nowrap;
      }
      .footer {
        text-align: center;
        padding: 36px 20px 8px;
        font-size: 0.78rem;
        color: #94a3b8;
        line-height: 2;
      }
      @media screen and (max-width: 600px) {
        .wrapper {
          padding: 12px 10px 36px;
        }
        .header {
          padding: 36px 20px 32px;
          border-radius: 12px;
        }
        .header h1 {
          font-size: 1.75rem;
        }
        .news-card {
          padding: 18px 16px;
          border-radius: 10px;
        }
        .news-card h3 {
          font-size: 1rem;
        }
        .card-footer {
          flex-direction: column;
          align-items: flex-start;
        }
      }
    </style>
  </head>
  <body>
    <div class="wrapper">
      <div class="container">
        <div class="header">
          <div class="header-eyebrow">Daily Brief</div>
          <h1>Buenos días, <span class="name">{user_name}</span></h1>
          <p class="subtitle">Tu resumen de noticias verificadas y actualizadas</p>
        </div>
        {sections}
        <div class="footer">
          <p>Daily Brief — Noticias verificadas de fuentes confiables.</p>
          <p>Actualizado diariamente con información clara y relevante.</p>
        </div>
      </div>
    </div>
  </body>
</html>
"""


def load_subscribers(path: str = "subscribers.csv") -> list[dict[str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo de suscriptores: {path}")

    subscribers: list[dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = (row.get("email") or "").strip()
            nombre = (row.get("nombre") or "").strip()
            activo = (row.get("activo") or "").strip().lower()
            if email:
                subscribers.append({"email": email, "nombre": nombre, "activo": activo})
    return subscribers


def build_prompt(region: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    return (
        "Eres un asistente especializado en obtener noticias verificadas y actualizadas. "
        f"Hoy es {today}. "
        "Genera exactamente 6 noticias REALES, VERIFICADAS Y ACTUALIZADAS de hoy o máximo los últimos 7 días para la región especificada. "
        "MUY IMPORTANTE: Cada noticia DEBE incluir la fecha de publicación. Las noticias NO pueden ser más de 7 días de antiguas. "
        "Divide cada noticia en seis campos: titulo, resumen, fuente, url, tema, fecha. "
        "La fecha debe estar en formato YYYY-MM-DD. "
        "Usa solamente estos temas: política, economía, tecnología, IA, fintech, criptomonedas, startups, ciencia. "
        "REQUISITOS CRÍTICOS DEL RESUMEN:\n"
        "- El resumen debe tener entre 100 y 150 palabras\n"
        "- Incluye datos concretos: números, nombres, hechos clave\n"
        "- Explica el qué, por qué y cómo de la noticia\n"
        "- No uses comillas dobles ni caracteres especiales dentro del resumen\n"
        "- NO hagas clickbait, sé claro e informativo\n"
        "REQUISITOS GENERALES:\n"
        "- Solo fuentes confiables y verificadas (Reuters, AP, Bloomberg, BBC, CNN, Guardian, etc)\n"
        "- Actualidad comprobada (no más de 7 días)\n"
        "- No repitas noticias que ya fueron enviadas en días anteriores\n"
        "- URLs válidas y funcionales\n"
        f"La región es: {region}. "
        "Llama a la herramienta guardar_noticias con las noticias encontradas. "
        "Si no hay 6 noticias disponibles, devuelve las mejores que tengas (mínimo 3)."
    )


def extract_json_from_response(text: str) -> Any:
    match = re.search(r"(\{\s*\"noticias\".*\}|\[.*\])", text, re.DOTALL)
    if not match:
        raise ValueError("No se encontró un bloque JSON válido en la respuesta del modelo")
    payload = match.group(1)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        # Eliminar caracteres de control que rompen el JSON
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', payload)
        return json.loads(cleaned)


def extract_text_from_response(result: dict[str, Any]) -> str:
    text = ""

    if isinstance(result.get("content"), list):
        text = "".join(
            item.get("text", "")
            for item in result["content"]
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
        )
    elif isinstance(result.get("completion"), str):
        text = result["completion"]
    elif isinstance(result.get("completion"), dict):
        completion = result["completion"]
        if isinstance(completion.get("content"), list):
            text = "".join(
                item.get("text", "")
                for item in completion["content"]
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
            )
    elif isinstance(result.get("message"), dict):
        message = result["message"]
        if isinstance(message.get("content"), str):
            text = message["content"]
        elif isinstance(message.get("content"), list):
            text = "".join(
                item.get("text", "")
                for item in message["content"]
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
            )
    elif isinstance(result.get("messages"), list):
        for message in result["messages"]:
            if isinstance(message, dict) and message.get("role") == "assistant":
                content = message.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "".join(
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
                    )
                break
    elif isinstance(result.get("output"), str):
        text = result["output"]
    elif isinstance(result.get("text"), str):
        text = result["text"]

    if not text:
        raise ValueError(
            "No se pudo extraer texto de la respuesta de Anthropic. "
            f"Respuesta completa: {json.dumps(result, ensure_ascii=False)[:2000]}"
        )

    return text


NEWS_TOOL = {
    "name": "guardar_noticias",
    "description": "Guarda las noticias encontradas para la región solicitada.",
    "input_schema": {
        "type": "object",
        "properties": {
            "noticias": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo":  {"type": "string"},
                        "resumen": {"type": "string"},
                        "fuente":  {"type": "string"},
                        "url":     {"type": "string"},
                        "tema":    {"type": "string", "enum": ["política", "economía", "tecnología", "IA", "fintech", "criptomonedas", "startups", "ciencia"]},
                        "fecha":   {"type": "string", "description": "Formato YYYY-MM-DD"},
                    },
                    "required": ["titulo", "resumen", "fuente", "url", "tema", "fecha"],
                },
            }
        },
        "required": ["noticias"],
    },
}


def fetch_news_for_region(region: str, api_key: str, max_retries: int = 3) -> list[dict[str, str]]:
    prompt = build_prompt(region)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": os.getenv("ANTHROPIC_API_VERSION", "2023-06-01"),
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [NEWS_TOOL],
        "tool_choice": {"type": "tool", "name": "guardar_noticias"},
        "max_tokens": 4096,
    }

    last_exc: Exception = RuntimeError("Sin intentos")
    for attempt in range(max_retries):
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Anthropic API error {response.status_code}: {response.text.strip() or exc}"
            ) from exc

        result = response.json()

        # Extraer el input del tool_use (siempre JSON válido garantizado por la API)
        try:
            tool_block = next(
                b for b in result.get("content", [])
                if isinstance(b, dict) and b.get("type") == "tool_use"
            )
            noticias = tool_block["input"]["noticias"]
        except (StopIteration, KeyError, TypeError) as exc:
            last_exc = exc
            print(f"  Respuesta inesperada en intento {attempt + 1}/{max_retries} para {region}, reintentando...")
            time.sleep(3)
            continue

        if not isinstance(noticias, list):
            raise ValueError("El campo 'noticias' debe ser una lista")

        return [
            {
                "titulo": str(item.get("titulo", "")).strip(),
                "resumen": str(item.get("resumen", "")).strip(),
                "fuente":  str(item.get("fuente", "")).strip(),
                "url":     str(item.get("url", "")).strip(),
                "tema":    str(item.get("tema", "")).strip(),
                "fecha":   str(item.get("fecha", datetime.now().strftime("%Y-%m-%d"))).strip(),
            }
            for item in noticias[:NEWS_PER_REGION]
        ]

    raise last_exc


def build_email_html(news_by_region: dict[str, list[dict[str, str]]], user_name: str = "suscriptor") -> str:
    sections = []
    for region, articles in news_by_region.items():
        cards = []
        for item in articles:
            fecha = item.get("fecha", datetime.now().strftime("%Y-%m-%d"))
            try:
                fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d de %B de %Y")
                # Traducir meses al español
                meses = {
                    "January": "enero", "February": "febrero", "March": "marzo",
                    "April": "abril", "May": "mayo", "June": "junio",
                    "July": "julio", "August": "agosto", "September": "septiembre",
                    "October": "octubre", "November": "noviembre", "December": "diciembre"
                }
                for en, es in meses.items():
                    fecha_formateada = fecha_formateada.replace(en, es)
            except:
                fecha_formateada = fecha
            
            cards.append(
                """
        <div class="news-card">
          <div class="card-meta">
            <span class="tag">{topic}</span>
            <span class="news-date">{date}</span>
          </div>
          <h3>{title}</h3>
          <p>{summary}</p>
          <div class="card-footer">
            <span class="news-source">Fuente: <a href="{url}">{source}</a></span>
            <a href="{url}" class="read-more">Leer más →</a>
          </div>
        </div>
        """.format(
                    date=escape_html(fecha_formateada),
                    title=escape_html(item["titulo"]),
                    summary=escape_html(item["resumen"]),
                    source=escape_html(item["fuente"]),
                    url=escape_html(item["url"]),
                    topic=escape_html(item["tema"]),
                )
            )
        sections.append(
            '<div class="section"><span class="section-label">{region}</span><div class="section-divider"></div><div class="section-content">{cards}</div></div>'.format(
                region=escape_html(region), cards="".join(cards)
            )
        )
    html = HTML_TEMPLATE.replace("{sections}", "\n".join(sections))
    html = html.replace("{user_name}", escape_html(user_name))
    return html


def escape_html(value: str) -> str:
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def load_sent_news(filepath: str = "sent_news.json") -> dict[str, list[str]]:
    """Carga el historial de noticias enviadas."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_sent_news(news_by_region: dict[str, list[dict[str, str]]], filepath: str = "sent_news.json") -> None:
    """Guarda el historial de noticias enviadas."""
    sent_news = load_sent_news(filepath)
    today = datetime.now().strftime("%Y-%m-%d")
    
    all_titles = []
    for region, articles in news_by_region.items():
        for article in articles:
            all_titles.append(article["titulo"])
    
    sent_news[today] = all_titles
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sent_news, f, ensure_ascii=False, indent=2)


def filter_recent_news(news_by_region: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    """Filtra noticias para evitar duplicados en días anteriores."""
    sent_news = load_sent_news()
    
    # Obtener títulos de las últimas 2 semanas
    recent_titles = set()
    for i in range(14):
        date_key = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_key in sent_news:
            recent_titles.update(sent_news[date_key])
    
    filtered = {}
    for region, articles in news_by_region.items():
        filtered[region] = [
            article for article in articles
            if article["titulo"] not in recent_titles
        ]
    
    return filtered


def build_plain_text(news_by_region: dict[str, list[dict[str, str]]]) -> str:
    lines = ["Daily Brief - Resumen de noticias\n"]
    for region, articles in news_by_region.items():
        lines.append(f"{region}\n")
        for item in articles:
            lines.append(f"- {item['titulo']} ({item['tema']})")
            lines.append(f"  Fuente: {item['fuente']}\n  URL: {item['url']}\n")
        lines.append("")
    return "\n".join(lines)


def send_email(
    smtp_user: str,
    smtp_password: str,
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp_user
    message["To"] = to_email

    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, message.as_string())


def collect_news(api_key: str) -> dict[str, list[dict[str, str]]]:
    news_by_region: dict[str, list[dict[str, str]]] = {}
    for region in REGIONS:
        print(f"Consultando noticias para {region}...")
        news_by_region[region] = fetch_news_for_region(region, api_key)
        print(f"  {len(news_by_region[region])} noticias obtenidas para {region}")
    return news_by_region


def main() -> None:
    parser = argparse.ArgumentParser(description="Envía un resumen diario de noticias por mail.")
    parser.add_argument("--dry-run", action="store_true", help="Solo genera el HTML y no envía mails.")
    parser.add_argument(
        "--test-email",
        type=str,
        help="Envia el mail únicamente a esta dirección para pruebas.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="brief_preview.html",
        help="Ruta donde se guarda el HTML generado cuando se usa --dry-run.",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    smtp_user = os.getenv("GMAIL_USER")
    smtp_password = os.getenv("GMAIL_APP_PASSWORD")

    if not api_key:
        raise SystemExit("Falta la variable de entorno ANTHROPIC_API_KEY.")
    if not smtp_user:
        raise SystemExit("Falta la variable de entorno GMAIL_USER.")
    if not smtp_password:
        raise SystemExit("Falta la variable de entorno GMAIL_APP_PASSWORD.")

    subscribers = load_subscribers()
    active_subscribers = [s for s in subscribers if s["activo"] == "si"]
    if args.test_email:
        active_subscribers = [{"email": args.test_email, "nombre": "Suscriptor de prueba", "activo": "si"}]

    if not active_subscribers:
        raise SystemExit("No se encontraron suscriptores activos.")

    news_by_region = collect_news(api_key)
    news_by_region = filter_recent_news(news_by_region)
    
    # Para el envío, usar el nombre del primer suscriptor activo (o suscriptor de prueba)
    subscriber_name = active_subscribers[0]["nombre"] or "suscriptor"
    
    html_body = build_email_html(news_by_region, subscriber_name)
    text_body = build_plain_text(news_by_region)
    subject = f"Daily Brief - Resumen de noticias ({datetime.now():%Y-%m-%d})"
    
    # Guardar noticias enviadas
    save_sent_news(news_by_region)

    if args.dry_run:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_body)
        print(f"Dry run completo. HTML guardado en {args.output}")
        return

    for subscriber in active_subscribers:
        email = subscriber["email"]
        nombre = subscriber["nombre"] or "suscriptor"
        print(f"Enviando a {email}...")
        try:
            send_email(smtp_user, smtp_password, email, nombre, subject, html_body, text_body)
            print(f"  Enviado a {email}")
        except Exception as exc:
            print(f"  Error al enviar a {email}: {exc}")


if __name__ == "__main__":
    main()
