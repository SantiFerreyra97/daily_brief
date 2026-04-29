# Daily Brief

Sistema automatizado de envío diario de resumen de noticias por mail.

## Estructura

- `send_brief.py`: script principal que consulta Anthropic, arma el HTML y envía el mail.
- `subscribers.csv`: lista de suscriptores activos / inactivos.
- `.github/workflows/daily_brief.yml`: workflow de GitHub Actions con cron diario y dispatch manual.

## Configuración local

1. Instala Python 3.11+.
2. Crea y activa un entorno virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Instala dependencias:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Define las variables de entorno:
   ```powershell
   setx ANTHROPIC_API_KEY "tu_api_key"
   setx GMAIL_USER "tu_mail@gmail.com"
   setx GMAIL_APP_PASSWORD "tu_app_password"
   ```
   Luego cierra la terminal y abre una nueva, o usa `set` solo para la sesión actual.

   Opcionalmente, puedes seleccionar otro modelo de Claude con:
   ```powershell
   setx ANTHROPIC_MODEL "claude-opus-4-7"
   ```

5. Edita `subscribers.csv` para agregar tus suscriptores y marca `activo` como `si` o `no`.

## Prueba local

- Generar el HTML sin enviar mails:
  ```powershell
  python send_brief.py --dry-run --output brief_preview.html
  ```

- Enviar solo a un mail de prueba:
  ```powershell
  python send_brief.py --test-email tu@mail.com
  ```

## GitHub Actions

El workflow se ejecuta todos los días a las `10:00 UTC` (07:00 Argentina) y también puede ejecutarse manualmente.

### Secrets necesarios

- `ANTHROPIC_API_KEY`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`

### Deploy

1. Sube el repositorio a GitHub.
2. En `Settings > Secrets and variables > Actions`, agrega los secretos.
3. El workflow se activa automáticamente y se puede lanzar manualmente desde la pestaña `Actions`.
