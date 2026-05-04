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

import feedparser
import requests
from time import mktime

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
NEWS_PER_REGION = 6
MAX_ARTICLE_AGE_DAYS = 2

REGIONS = ["Internacional", "USA", "Europa", "Argentina"]

RSS_FEEDS: dict[str, list[str]] = {
    "Internacional": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://feeds.apnews.com/rss/apf-topnews",
        "https://feeds.bbci.co.uk/mundo/noticias/rss.xml",
    ],
    "USA": [
        "https://feeds.npr.org/1001/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "https://www.theguardian.com/us-news/rss",
        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    ],
    "Europa": [
        "https://rss.dw.com/rdf/rss-en-world",
        "https://www.france24.com/en/europe/rss",
        "https://www.theguardian.com/world/europe-news/rss",
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    ],
    "Argentina": [
        "https://www.infobae.com/feeds/rss/",
        "https://chequeado.com/feed/",
        "https://www.lanacion.com.ar/arcio/rss/",
        "https://feeds.bbci.co.uk/mundo/noticias/america_latina/rss.xml",
    ],
}

REGION_COLORS: dict[str, dict[str, str]] = {
    "Internacional": {
        "accent":   "#2563eb",
        "tag_bg":   "#eff6ff",
        "tag_text": "#1d4ed8",
        "title":    "#1e3a5f",
        "label":    "#1d4ed8",
    },
    "USA": {
        "accent":   "#dc2626",
        "tag_bg":   "#fee2e2",
        "tag_text": "#b91c1c",
        "title":    "#7f1d1d",
        "label":    "#dc2626",
    },
    "Europa": {
        "accent":   "#16a34a",
        "tag_bg":   "#dcfce7",
        "tag_text": "#15803d",
        "title":    "#14532d",
        "label":    "#16a34a",
    },
    "Argentina": {
        "accent":   "#d97706",
        "tag_bg":   "#fef9c3",
        "tag_text": "#b45309",
        "title":    "#78350f",
        "label":    "#d97706",
    },
}

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
        font-size: 1rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 3px;
        color: #1e293b;
        margin-bottom: 8px;
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


def fetch_rss_articles(region: str) -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    cutoff = datetime.now() - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    for feed_url in RSS_FEEDS.get(region, []):
        try:
            feed = feedparser.parse(feed_url)
            feed_title = feed.feed.get("title", feed_url.split("/")[2])
            for entry in feed.entries[:20]:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                published = entry.get("published", "")

                # Filtrar artículos con más de MAX_ARTICLE_AGE_DAYS días
                pub_struct = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub_struct:
                    try:
                        pub_dt = datetime.fromtimestamp(mktime(pub_struct))
                        if pub_dt < cutoff:
                            continue
                    except (OverflowError, OSError, ValueError):
                        pass

                if title and link:
                    articles.append({
                        "titulo": title,
                        "descripcion": re.sub(r"<[^>]+>", "", summary)[:400],
                        "url": link,
                        "fuente": feed_title,
                        "fecha_pub": published,
                    })
        except Exception as exc:
            print(f"  Warning: error en feed {feed_url}: {exc}")
    return articles[:30]


def build_prompt(region: str, raw_articles: list[dict[str, str]]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    articles_text = "\n\n".join(
        f"[{i+1}] Título: {a['titulo']}\n"
        f"    Fuente: {a['fuente']}\n"
        f"    URL: {a['url']}\n"
        f"    Fecha: {a['fecha_pub']}\n"
        f"    Descripción: {a['descripcion']}"
        for i, a in enumerate(raw_articles)
    )
    return (
        f"Hoy es {today}. Estos son artículos REALES obtenidos de fuentes confiables para la región {region}:\n\n"
        f"{articles_text}\n\n"
        "Selecciona los 6 más relevantes e interesantes siguiendo ESTAS REGLAS ESTRICTAS:\n"
        "- Solo incluir noticias con fecha de publicación dentro de los últimos 2 días\n"
        "- NO repetir noticias sobre el mismo tema o evento aunque vengan de distintas fuentes\n"
        "- Si dos artículos cubren el mismo hecho, elige el de la fuente más reconocida\n"
        "- Para cada noticia seleccionada:\n"
        "  * Escribe un resumen en español claro y detallado de 100-150 palabras\n"
        "  * USA EXACTAMENTE la URL y fuente del artículo (no las modifiques ni inventes otras)\n"
        "  * Usa la fecha de publicación en formato YYYY-MM-DD\n"
        "  * Asigna el tema más apropiado\n"
        "Llama a la herramienta guardar_noticias con los artículos seleccionados. "
        "Si hay menos de 6, devuelve todos los disponibles."
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
    raw_articles = fetch_rss_articles(region)
    print(f"  {len(raw_articles)} artículos RSS obtenidos para {region}")
    if not raw_articles:
        raise RuntimeError(f"No se pudieron obtener artículos RSS para {region}")
    prompt = build_prompt(region, raw_articles)
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
            
            color = REGION_COLORS.get(region, REGION_COLORS["Internacional"])
            cards.append(
                """
        <div class="news-card">
          <div class="card-meta">
            <span class="tag" style="background:{tag_bg};color:{tag_text}">{topic}</span>
            <span class="news-date">{date}</span>
          </div>
          <h3 style="color:{title_color}">{title}</h3>
          <p>{summary}</p>
          <div class="card-footer">
            <span class="news-source">Fuente: <a href="{url}" style="color:{accent}">{source}</a></span>
            <a href="{url}" class="read-more" style="color:{accent}">Leer más →</a>
          </div>
        </div>
        """.format(
                    date=escape_html(fecha_formateada),
                    title=escape_html(item["titulo"]),
                    summary=escape_html(item["resumen"]),
                    source=escape_html(item["fuente"]),
                    url=escape_html(item["url"]),
                    topic=escape_html(item["tema"]),
                    tag_bg=color["tag_bg"],
                    tag_text=color["tag_text"],
                    title_color=color["title"],
                    accent=color["accent"],
                )
            )
        color = REGION_COLORS.get(region, REGION_COLORS["Internacional"])
        sections.append(
            '<div class="section">'
            '<span class="section-label" style="color:{label_color}">{region}</span>'
            '<div class="section-divider" style="background:linear-gradient(to right,{accent} 0%,transparent 70%)"></div>'
            '<div class="section-content">{cards}</div>'
            '</div>'.format(
                region=escape_html(region),
                cards="".join(cards),
                label_color=color["label"],
                accent=color["accent"],
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


def deduplicate_across_regions(news_by_region: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    """Elimina noticias cuyo título ya apareció en una región anterior."""
    seen: set[str] = set()
    result: dict[str, list[dict[str, str]]] = {}
    for region in REGIONS:
        articles = news_by_region.get(region, [])
        unique = []
        for article in articles:
            norm = re.sub(r"[^\w\s]", "", article["titulo"].lower()).strip()
            if norm not in seen:
                seen.add(norm)
                unique.append(article)
        removed = len(articles) - len(unique)
        if removed:
            print(f"  Dedup entre regiones: {removed} duplicado(s) eliminado(s) en {region}")
        result[region] = unique
    return result


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
    news_by_region = deduplicate_across_regions(news_by_region)
    save_sent_news(news_by_region)

    text_body = build_plain_text(news_by_region)
    subject = f"Daily Brief - Resumen de noticias ({datetime.now():%Y-%m-%d})"

    if args.dry_run:
        first_name = active_subscribers[0]["nombre"] or "suscriptor"
        html_body = build_email_html(news_by_region, first_name)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_body)
        print(f"Dry run completo. HTML guardado en {args.output}")
        return

    for subscriber in active_subscribers:
        email = subscriber["email"]
        nombre = subscriber["nombre"] or "suscriptor"
        html_body = build_email_html(news_by_region, nombre)
        print(f"Enviando a {email}...")
        try:
            send_email(smtp_user, smtp_password, email, nombre, subject, html_body, text_body)
            print(f"  Enviado a {email}")
        except Exception as exc:
            print(f"  Error al enviar a {email}: {exc}")


if __name__ == "__main__":
    main()
