#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import smtplib
from datetime import datetime
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
      body {
        margin: 0;
        padding: 0;
        background: #f5f3ee;
        font-family: Georgia, serif;
        color: #2c2c2c;
      }
      .container {
        max-width: 720px;
        margin: 0 auto;
        padding: 24px;
      }
      .header {
        background: #101010;
        color: #ffffff;
        padding: 32px 24px;
        border-radius: 16px;
        text-align: center;
      }
      .header h1 {
        margin: 0;
        font-size: 2.1rem;
      }
      .header p {
        margin: 12px 0 0;
        color: #c7c7c7;
      }
      .section {
        margin-top: 24px;
      }
      .section h2 {
        margin-bottom: 16px;
        font-size: 1.4rem;
        border-bottom: 2px solid #d7ccc8;
        padding-bottom: 8px;
      }
      .news-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.05);
      }
      .news-card h3 {
        margin: 0 0 10px;
        font-size: 1.1rem;
      }
      .news-card p {
        margin: 0 0 10px;
        line-height: 1.5;
        color: #4a4a4a;
      }
      .news-meta {
        font-size: 0.95rem;
        color: #6f6f6f;
      }
      .tag {
        display: inline-block;
        margin-top: 10px;
        padding: 6px 10px;
        border-radius: 999px;
        background: #ece1d4;
        color: #5b3a29;
        font-size: 0.85rem;
      }
      .footer {
        margin-top: 32px;
        font-size: 0.95rem;
        color: #5b5b5b;
        text-align: center;
      }
      a {
        color: #1b4d95;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h1>Daily Brief</h1>
        <p>Resumen diario de noticias: internacional, USA, Europa y Argentina.</p>
      </div>
      {sections}
      <div class="footer">
        <p>Este mail fue generado automáticamente con Anthropic + Gmail SMTP.</p>
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
    return (
        "Eres un asistente de resúmenes de noticias con acceso a búsqueda web actualizada. "
        "Genera exactamente 6 noticias reales del día para la región especificada. "
        "Divide cada noticia en cinco campos: titulo, resumen, fuente, url y tema. "
        "Usa solamente estos temas: política, economía, tecnología, IA, fintech, criptomonedas, startups, ciencia. "
        "Devuelve una única estructura JSON válida con el siguiente formato:\n"
        "{\"noticias\": [ {\"titulo\": \"...\", \"resumen\": \"...\", \"fuente\": \"...\", \"url\": \"...\", \"tema\": \"...\"} ]} \n"
        "No agregues texto previo ni posterior. No envíes comentarios, explicaciones ni etiquetas fuera del JSON. "
        f"La región es: {region}. "
        "Si no hay 6 noticias disponibles de la región, devuelve las mejores 6 noticias posibles en formato JSON válido."
    )


def extract_json_from_response(text: str) -> Any:
    match = re.search(r"(\{\s*\"noticias\".*\}|\[.*\])", text, re.DOTALL)
    if not match:
        raise ValueError("No se encontró un bloque JSON válido en la respuesta del modelo")
    payload = match.group(1)
    return json.loads(payload)


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


def fetch_news_for_region(region: str, api_key: str) -> list[dict[str, str]]:
    prompt = build_prompt(region)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": os.getenv("ANTHROPIC_API_VERSION", "2023-06-01"),
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1700,
    }

    response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Anthropic API error {response.status_code}: {response.text.strip() or exc}"
        ) from exc

    result = response.json()
    text = extract_text_from_response(result)

    data = extract_json_from_response(text)
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
        }
        for item in noticias[:NEWS_PER_REGION]
    ]


def build_email_html(news_by_region: dict[str, list[dict[str, str]]]) -> str:
    sections = []
    for region, articles in news_by_region.items():
        cards = []
        for item in articles:
            cards.append(
                """
        <div class=\"news-card\">
          <h3>{title}</h3>
          <p>{summary}</p>
          <div class=\"news-meta\">Fuente: <a href=\"{url}\">{source}</a></div>
          <div class=\"tag\">{topic}</div>
        </div>
        """.format(
                    title=escape_html(item["titulo"]),
                    summary=escape_html(item["resumen"]),
                    source=escape_html(item["fuente"]),
                    url=escape_html(item["url"]),
                    topic=escape_html(item["tema"]),
                )
            )
        sections.append(
            "<div class=\"section\"><h2>{region}</h2>{cards}</div>".format(
                region=escape_html(region), cards="".join(cards)
            )
        )
    return HTML_TEMPLATE.replace("{sections}", "\n".join(sections))


def escape_html(value: str) -> str:
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


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
    html_body = build_email_html(news_by_region)
    text_body = build_plain_text(news_by_region)
    subject = f"Daily Brief - Resumen de noticias ({datetime.utcnow():%Y-%m-%d})"

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
