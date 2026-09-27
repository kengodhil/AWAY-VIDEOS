# AWAY Videos

No-login public video site. Visitors watch a **5-second teaser**, pay **TZS 2,000** via Snippe (mobile money USSD) to unlock the full video for this browser session, and optionally pay **TZS 1,000** to download.

## Why videos disappear after redeploy

Render **deletes the server disk** on every deploy. Titles stay in **Neon** (database), but video **files** were only on that disk — so the home page showed titles with no playable file.

**Fix:** store uploads on **Cloudinary** (free). Files stay online after every redeploy.

## Cloudinary setup (required on Render)

1. Sign up free: https://cloudinary.com/users/register/free  
2. Dashboard → **API Keys** → copy **API Environment variable**  
   Looks like:
   ```text
   cloudinary://123456789012345:xxxxxxxxxxxxxxxx@your_cloud_name
   ```
3. **Render** → `away-videos` → **Environment** → Add:
   - **Key:** `CLOUDINARY_URL`
   - **Value:** paste that full string
4. Save → **Manual Deploy**
5. Open **Studio** → delete old broken videos (file was lost) → **Upload video again**  
   New uploads go to Cloudinary and **survive redeploys**.

## Neon Postgres

Set `DATABASE_URL` on Render to your Neon connection URI.

## Admin (Studio)

| Field | Value |
|--------|--------|
| URL | `/studio/login/` |
| Username | `admin` |
| Password | `admin123` |

## Run locally

```bash
pip install -r requirements.txt
copy .env.example .env
# optional: DATABASE_URL=... and CLOUDINARY_URL=...
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Render start command

```text
python manage.py migrate --no-input && python manage.py seed_demo && gunicorn awayvideos.wsgi:application
```
