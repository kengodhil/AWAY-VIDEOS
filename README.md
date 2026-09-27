# AWAY Videos

No-login public video site. Visitors watch a **5-second teaser**, pay **TZS 2,000** via Snippe (mobile money USSD) to unlock the full video for this browser session, and optionally pay **TZS 1,000** to download.

## Public flow

1. Home page — video grid (2 columns on phones).
2. Each card autoplays a muted 5s teaser.
3. **Watch now** → phone number → USSD → full player.
4. Player download icon → pay TZS 1,000 → download.
5. New browser session → pay again to watch.

## Admin (Studio)

Bottom-left **Admin** opens branded login at `/studio/login/` (same teal/white UI — not Django’s default admin).

Admins can upload/delete videos, view payments, and add other admins.

### Login credentials

| Field | Value |
|--------|--------|
| URL | `/studio/login/` |
| Username | `admin` |
| Password | `admin123` |

The account is **created automatically** on every deploy (`seed_demo` in build + start). No Shell required.

**Change this password** before public use (or add a new admin and stop using the default).

## Run locally

```bash
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

- Site: http://127.0.0.1:8000/
- Studio: http://127.0.0.1:8000/studio/login/ — `admin` / `admin123`

## Snippe live keys

```
SNIPPE_MOCK=false
SNIPPE_API_KEY=snp_...
SNIPPE_WEBHOOK_URL=https://your-domain/webhooks/snippe/
```

## Render

- Build runs: migrate + `seed_demo`
- Start runs: migrate + `seed_demo` + gunicorn

If the dashboard **Start Command** was set manually, use:

```text
python manage.py migrate --no-input && python manage.py seed_demo && gunicorn awayvideos.wsgi:application
```
