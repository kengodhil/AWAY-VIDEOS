# AWAY Videos

No-login video site. Visitors watch a **5-second teaser**, pay **TZS 2,000** via Snippe (mobile money USSD) to unlock the full video for this browser session, and optionally pay **TZS 1,000** to download.

## Flow

1. Open the home page — videos in a responsive grid (2 columns on phones).
2. Each card autoplays a muted 5s teaser.
3. **Watch now** → enter phone number → USSD prompt → unlock full player.
4. On the player, bottom-right **download** icon → second payment (TZS 1,000) → file downloads.
5. Closing the browser / ending the session means paying again to watch.

Admin only: `/admin/` to upload videos (not shown on the public site).

## Run locally

```bash
python -m venv .venv
# PowerShell if scripts blocked:
#   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
pip install -r requirements.txt
copy .env.example .env
# Fresh DB after redesign:
del db.sqlite3
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

- Public site: no login
- Admin: http://127.0.0.1:8000/admin/ — `admin` / `admin123`

With `SNIPPE_MOCK=true` (default), payment screens have a **Confirm demo payment** button.

## Snippe live keys

```
SNIPPE_MOCK=false
SNIPPE_API_KEY=snp_...
SNIPPE_WEBHOOK_URL=https://your-domain/webhooks/snippe/
```

Docs: https://docs.snippe.sh/

## Render

- Build: `./build.sh`
- Start: `gunicorn awayvideos.wsgi:application`
- Set `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `SNIPPE_*` as needed

## Branding

Site name is **AWAY Videos** everywhere (teal + gold).
