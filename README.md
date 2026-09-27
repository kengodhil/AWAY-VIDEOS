# AWAY Videos

No-login public video site. Visitors watch a **5-second teaser**, pay **TZS 2,000** via Snippe (mobile money USSD) to unlock the full video for this browser session, and optionally pay **TZS 1,000** to download.

## Public flow

1. Home page — video grid (2 columns on phones).
2. Each card autoplays a muted 5s teaser.
3. **Watch now** → phone number → USSD → full player.
4. Player download icon → pay TZS 1,000 → download.
5. New browser session → pay again to watch.

## Admin (Studio)

The bottom-left **Admin** button opens a **branded login** (same teal/white UI as the site — not the default Django admin).

After login, admins can:

- Upload / delete videos
- View all payments
- Add other admins

### Default credentials

| Field | Value |
|--------|--------|
| URL | `/studio/login/` |
| Username | `admin` |
| Password | `admin123` |

Create the account after migrate:

```bash
python manage.py seed_demo
```

On Render Shell, run the same command once after deploy.

**Change this password** before any public use.

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

With `SNIPPE_MOCK=true` (default), payments use **Confirm demo payment**.

## Snippe live keys

```
SNIPPE_MOCK=false
SNIPPE_API_KEY=snp_...
SNIPPE_WEBHOOK_URL=https://your-domain/webhooks/snippe/
```

Docs: https://docs.snippe.sh/

## Render

- Build: `./build.sh`
- Start: `python manage.py migrate --no-input && gunicorn awayvideos.wsgi:application`
- Then in Shell: `python manage.py seed_demo`

## Branding

**AWAY Videos** — teal + gold / white UI.
