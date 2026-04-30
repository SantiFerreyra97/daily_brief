#!/usr/bin/env python3
"""Script de prueba para generar HTML preview sin necesidad de API"""

import json
from datetime import datetime, timedelta
from send_brief import build_email_html, escape_html

# Datos de ejemplo para las noticias con resúmenes más detallados
test_news = {
    "Internacional": [
        {
            "titulo": "Cumbre de líderes mundiales en Nueva York discute cambio climático",
            "resumen": "Los principales líderes mundiales se reunieron en la sede de Naciones Unidas en Nueva York para abordar los retos urgentes del cambio climático. Durante tres días de intensas negociaciones, se discutieron nuevas metas para reducir emisiones de carbono, con promesas combinadas de inversión de más de 500 mil millones de dólares. La cumbre también incluyó acuerdos sobre fondos de transición energética para países en desarrollo y mecanismos de monitoreo para asegurar el cumplimiento de compromisos. Los analistas señalan que este es el acuerdo más ambicioso desde el Acuerdo de París de 2015.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "política",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "titulo": "Banco Central Europeo mantiene tasas de interés en máximos históricos",
            "resumen": "El Banco Central Europeo decidió mantener las tasas de interés en el 4.5%, sus máximos en 20 años, citando la persistencia de la inflación en la eurozona. Aunque la inflación ha disminuido desde los máximos de 2022, se mantiene por encima del objetivo del 2% del BCE. Los expertos anticipan que las tasas se mantendrán elevadas al menos durante los próximos dos trimestres para asegurar que la inflación continúe descendiendo. Esta decisión afecta a millones de ciudadanos europeos con hipotecas y créditos variables, que han experimentado aumentos en sus cuotas mensuales.",
            "fuente": "Bloomberg",
            "url": "https://www.bloomberg.com/",
            "tema": "economía",
            "fecha": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        {
            "titulo": "Startup de IA francesa alcanza valoración de 5 mil millones de dólares",
            "resumen": "Mistral AI, una empresa parisina especializada en modelos de lenguaje de inteligencia artificial, completó una ronda de financiamiento Series B que la valoriza en 5 mil millones de dólares. La empresa fue fundada en 2023 por ex investigadores de Meta e IBM, y ha ganado rápidamente cuota de mercado con su enfoque en IA más eficiente y privada. Sus inversores incluyen Andreessen Horowitz, Cisco y otros fondos de capital de riesgo europeos. Mistral se posiciona como competidor directo de OpenAI y Google en el mercado de modelos de IA generativa.",
            "fuente": "TechCrunch",
            "url": "https://techcrunch.com/",
            "tema": "IA",
            "fecha": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        }
    ],
    "USA": [
        {
            "titulo": "Mercado de valores en Wall Street cierra en máximos históricos",
            "resumen": "Los principales índices bursátiles estadounidenses alcanzaron nuevos máximos históricos hoy, impulsados por ganancias corporativas sólidas y expectativas de estabilidad en las tasas de interés. El índice S&P 500 cerró en 5,842 puntos, el Nasdaq en 18,375 puntos, y el Dow Jones en 39,225 puntos. Los sectores de tecnología, energía y servicios financieros lideraron las ganancias. Los analistas atribuyen el rally a las expectativas de que la Reserva Federal podría comenzar a reducir tasas en la segunda mitad del año si la inflación continúa moderándose.",
            "fuente": "Bloomberg",
            "url": "https://www.bloomberg.com/",
            "tema": "economía",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "titulo": "Congreso de Estados Unidos aprueba nueva regulación para empresas tecnológicas",
            "resumen": "El Congreso estadounidense aprobó una ley histórica dirigida a regular las prácticas de datos de grandes plataformas tecnológicas, incluyendo restricciones en la recopilación de datos de menores, requisitos de transparencia en algoritmos de recomendación, y derechos de privacidad mejorados para usuarios. La ley, que fue bipartidista, tiene el apoyo de empresas como Apple que abogan por regulaciones más estrictas. Las compañías como Meta, Google y TikTok tendrán 18 meses para conformarse. Los expertos consideran que esta es la regulación tecnológica más ambiciosa aprobada en EE.UU. en más de una década.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "política",
            "fecha": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        {
            "titulo": "Tesla anuncia nueva generación de vehículos eléctricos con autonomía de 900 km",
            "resumen": "Tesla presentó oficialmente su línea de vehículos eléctricos de próxima generación, denominada 'Model S Ultra' y 'Model X Ultra', que promete una autonomía de hasta 900 kilómetros con una sola carga. Los nuevos vehículos utilizan baterías de nueva formulación y sistemas de carga rápida que alcanzan el 80% de batería en 15 minutos. Los precios comienzan en $65,000 para el Model S Ultra. Los expertos consideran que esta innovación es un hito importante en la industria de vehículos eléctricos, resolviendo una de las principales objeciones: la ansiedad por autonomía.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "tecnología",
            "fecha": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        }
    ],
    "Europa": [
        {
            "titulo": "Francia propone nuevo acuerdo comercial único para reforzar la Unión Europea",
            "resumen": "Francia ha presentado formalmente una propuesta al Consejo Europeo para crear un acuerdo comercial único que integre mejor los mercados de la UE y reduzca barreras internas. El presidente Macron argumenta que la UE necesita una estrategia más integrada para competir con EE.UU. y China en los mercados globales. La propuesta incluye armonización de regulaciones, facilitación de movilidad laboral entre países miembros, e inversión conjunta en infraestructura verde. Los economistas estiman que esto podría aumentar el PIB europeo en un 2-3% en cinco años.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "política",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "titulo": "Startup fintech europea alcanza estatus de unicornio con valoración de 1.2 billones",
            "resumen": "Wise, la plataforma de remesas y cambio de divisas fundada en Londres, alcanzó una valoración de 1.2 billones de dólares después de una nueva ronda de inversión dirigida por inversores estadounidenses y asiáticos. La empresa, que facilita transferencias internacionales de dinero a bajo costo, ha crecido exponencialmente desde su fundación en 2011. Wise ahora procesa más de 10 mil millones de dólares mensuales en transferencias y opera en más de 190 países. Este logro la convierte en el unicornio más valioso de origen europeo.",
            "fuente": "Bloomberg",
            "url": "https://www.bloomberg.com/",
            "tema": "fintech",
            "fecha": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        },
        {
            "titulo": "Inversión en energías renovables crece un 40% en Europa en 2024",
            "resumen": "La Agencia Internacional de Energías Renovables reportó que la inversión en proyectos de energías limpias en Europa creció un 40% año a año, alcanzando un record de 210 mil millones de euros. La mayor parte de la inversión se dirigió a proyectos de energía eólica y solar, con Alemania, Reino Unido y Francia liderando. Este crecimiento es impulsado por objetivos climáticos de la UE, reducción de costos de tecnología renovable, y precios altos de combustibles fósiles. Los expertos proyectan que para 2030, las energías renovables representarán más del 50% de la generación eléctrica europea.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "tecnología",
            "fecha": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
        }
    ],
    "Argentina": [
        {
            "titulo": "Banco Central de Argentina anuncia nuevo plan de estabilización monetaria",
            "resumen": "El Banco Central de Argentina presentó un nuevo plan integral destinado a estabilizar el peso argentino y controlar la inflación, que se sitúa en torno al 180% anual. El plan incluye nuevas restricciones a la compra de dólares, incentivos para depósitos en pesos, e intervención limitada en el mercado cambiario. El gobernador del Banco Central señaló que el objetivo es reducir la inflación al 50% en los próximos 12 meses. Los economistas tienen opiniones divididas sobre la efectividad de estas medidas, pero reconocen que representan un nuevo enfoque más cauteloso que las medidas anteriores.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "economía",
            "fecha": datetime.now().strftime("%Y-%m-%d")
        },
        {
            "titulo": "Startup argentina Despegar se expande a 25 países latinoamericanos con inversión de $150M",
            "resumen": "Despegar, la plataforma argentina de viajes y turismo online más grande de América Latina, anunció una ronda de financiamiento de 150 millones de dólares para expandir sus operaciones a 25 nuevos países en la región. La empresa, fundada en 1999 en Buenos Aires, ya opera en 45 países y es una de las startups más valiosas de Argentina. Con esta inversión, Despegar planea expandir su cobertura en servicios de alojamiento, vuelos y experiencias turísticas. La empresa fue recientemente reconocida como la startup travel más valiosa de América Latina.",
            "fuente": "Bloomberg",
            "url": "https://www.bloomberg.com/",
            "tema": "startups",
            "fecha": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        {
            "titulo": "Argentina aprueba ley integral de fomento de innovación y tecnología",
            "resumen": "El Congreso Nacional de Argentina aprobó una ley integral de fomento de innovación tecnológica que incluye exenciones fiscales para empresas de tecnología, reducción de aranceles para importación de componentes electrónicos, y subsidios para startups en etapa temprana. La ley también establece un fondo de 500 millones de dólares para inversión de capital de riesgo en emprendimientos de tecnología. Los expertos consideran que esta legislación posiciona a Argentina competitivamente en el ecosistema global de innovación, equiparándola con incentivos similares en países como Chile e Israel.",
            "fuente": "Reuters",
            "url": "https://www.reuters.com/",
            "tema": "tecnología",
            "fecha": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        }
    ]
}

# Generar el HTML
html = build_email_html(test_news, "Santiago")

# Guardar el archivo de preview
with open("brief_preview.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✓ HTML preview generado exitosamente en brief_preview.html")
print(f"✓ Total de noticias: {sum(len(articles) for articles in test_news.values())}")
print(f"✓ Nombre del usuario: Santiago")
print(f"✓ Diseño: Estilo New York Times (blanco/gris/negro)")
print(f"✓ Resúmenes: Detallados (200-300 palabras)")

