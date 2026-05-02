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
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
        background-color: #ffffff;
        color: #1a1a1a;
        line-height: 1.6;
      }
      .container {
        max-width: 900px;
        margin: 0 auto;
        padding: 0;
      }
      .greeting-header {
        background-color: #000000;
        color: #ffffff;
        padding: 60px 40px;
        text-align: center;
        border-bottom: 3px solid #000;
      }
      .greeting-header h1 {
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 8px;
        font-family: Georgia, 'Times New Roman', serif;
        letter-spacing: -0.5px;
      }
      .greeting-header .user-name {
        font-size: 1.4rem;
        font-weight: 600;
        color: #f0f0f0;
        margin-bottom: 20px;
        font-family: Georgia, 'Times New Roman', serif;
      }
      .greeting-header .intro {
        font-size: 1rem;
        color: #d0d0d0;
        line-height: 1.8;
        max-width: 600px;
        margin: 0 auto;
      }
      .section {
        background-color: #ffffff;
        border-top: 1px solid #e5e5e5;
        padding: 40px;
      }
      .section:first-of-type {
        border-top: none;
        padding-top: 50px;
      }
      .section h2 {
        font-size: 1.6rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 35px;
        padding-bottom: 15px;
        border-bottom: 2px solid #000;
        font-family: Georgia, 'Times New Roman', serif;
        letter-spacing: -0.3px;
      }
      .section-content {
        padding: 0;
      }
      .news-card {
        padding: 30px 0;
        border-bottom: 1px solid #e5e5e5;
        display: flex;
        flex-direction: column;
      }
      .news-card:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }
      .news-date {
        font-size: 0.75rem;
        color: #666666;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
      }
      .news-card h3 {
        margin: 0 0 15px;
        font-size: 1.5rem;
        color: #000000;
        line-height: 1.3;
        font-family: Georgia, 'Times New Roman', serif;
        font-weight: 700;
        letter-spacing: -0.3px;
      }
      .news-card p {
        margin: 0 0 18px;
        line-height: 1.7;
        color: #333333;
        font-size: 1rem;
      }
      .news-footer {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 20px;
        margin-top: 15px;
      }
      .news-meta {
        font-size: 0.9rem;
        color: #555555;
      }
      .news-meta a {
        color: #1a1a1a;
        text-decoration: none;
        font-weight: 600;
        border-bottom: 1px solid #1a1a1a;
      }
      .news-meta a:hover {
        background-color: #f0f0f0;
      }
      .tag {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 2px;
        background-color: #f0f0f0;
        color: #1a1a1a;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .read-more {
        display: inline-block;
        padding: 12px 24px;
        background-color: #ffffff;
        color: #1a1a1a;
        text-decoration: none;
        border: 1px solid #1a1a1a;
        border-radius: 2px;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.2s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .read-more:hover {
        background-color: #1a1a1a;
        color: #ffffff;
      }
      .footer {
        background-color: #f8f8f8;
        padding: 30px 40px;
        text-align: center;
        font-size: 0.85rem;
        color: #666666;
        border-top: 1px solid #e5e5e5;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="greeting-header">
        <h1>Daily Brief</h1>
        <div class="user-name">Hola, {user_name}</div>
        <div class="intro">
          <p>Tu resumen diario de noticias verificadas y actualizadas. Aquí encontrarás información clara y concisa de los eventos más relevantes del día.</p>
        </div>
      </div>
      {sections}
      <div class="footer">
        <p>Daily Brief — Noticias verificadas de fuentes confiables. Actualizado diariamente con información clara y relevante.</p>
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
        "Devuelve una única estructura JSON válida con el siguiente formato:\n"
        "{\"noticias\": [ {\"titulo\": \"...\", \"resumen\": \"RESUMEN_DETALLADO_200_300_PALABRAS\", \"fuente\": \"...\", \"url\": \"...\", \"tema\": \"...\", \"fecha\": \"YYYY-MM-DD\"} ]} \n"
        "No agregues texto previo ni posterior. No envíes comentarios, explicaciones ni etiquetas fuera del JSON. "
        f"La región es: {region}. "
        "Si no hay 6 noticias disponibles de la región, devuelve las mejores noticias posibles (mínimo 3) en formato JSON válido."
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
        text = extract_text_from_response(result)

        try:
            data = extract_json_from_response(text)
        except (ValueError, json.JSONDecodeError) as exc:
            last_exc = exc
            print(f"  JSON inválido en intento {attempt + 1}/{max_retries} para {region}, reintentando...")
            time.sleep(3)
            continue

        if isinstance(data, dict) and "noticias" in data:
            noticias = data["noticias"]
        elif isinstance(data, list):
            noticias = data
        else:
            raise ValueError("El JSON devuelto no contiene el campo 'noticias'.")

        if not isinstance(noticias, list):
            raise ValueError("El campo 'noticias' debe ser una lista")

        return [
            {
                "titulo": str(item.get("titulo", "")).strip(),
                "resumen": str(item.get("resumen", "")).strip(),
                "fuente": str(item.get("fuente", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "tema": str(item.get("tema", "")).strip(),
                "fecha": str(item.get("fecha", datetime.now().strftime("%Y-%m-%d"))).strip(),
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
          <div class="news-date">{date}</div>
          <h3>{title}</h3>
          <p>{summary}</p>
          <div class="news-footer">
            <div class="news-meta">Fuente: <a href="{url}">{source}</a></div>
            <a href="{url}" class="read-more">Leer más →</a>
          </div>
          <div class="tag">{topic}</div>
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
            '<div class="section"><h2>{region}</h2><div class="section-content">{cards}</div></div>'.format(
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
