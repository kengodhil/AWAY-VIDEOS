# AWAY VIDEOS

Simple Django website for paid videos. A viewer enters a Tanzania mobile number. The app sends a Selcom wallet-payment prompt. After a successful payment, the video unlocks.

## How it works for a new user

1. Create an account.
2. Open a video and tap **Pay with mobile number**.
3. Enter the phone number linked to mobile money (M-Pesa, Tigo Pesa, Airtel Money, and similar).
4. Approve the Selcom prompt on the phone.
5. Watch the video.

Admin users can add videos, delete videos, and delete users at `/studio/`.

## Colours

The interface uses two colours: deep teal and gold.

## Run locally

```bash
python3 -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

Demo admin login:

- Username: `admin`
- Password: `admin123`

With `SELCOM_MOCK=true` (the default), the payment screen has a demo confirm button so you can test without live Selcom keys.

## Deploy on Render

1. Push this repo to GitHub.
2. In [Render](https://render.com) → **New → Blueprint** and connect the repo (uses `render.yaml`), **or** create a **Web Service** manually:
   - **Runtime:** Python
   - **Build command:** `./build.sh`
   - **Start command:** `gunicorn awayvideos.wsgi:application`
3. Set environment variables (Blueprint already sets most of these):

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | Generate a long random string |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com` (or your custom domain) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `SELCOM_MOCK` | `true` until you have live keys |

4. After deploy, open **Render Shell** once and run:

```bash
python manage.py seed_demo
```

**Note:** Render’s free disk is ephemeral. SQLite and uploaded videos under `media/` will be wiped on redeploy. For production, switch to Postgres + object storage (e.g. S3 / Cloudinary) later.

## Live Selcom setup

Ask Selcom for an API key, API secret, and vendor/till ID. Put them in `.env` (or Render env vars):

```
SELCOM_MOCK=false
SELCOM_API_KEY=your-key
SELCOM_API_SECRET=your-secret
SELCOM_VENDOR=your-vendor-id
SELCOM_WEBHOOK_URL=https://your-public-domain/webhooks/selcom/
```

The live flow is:

1. `POST /v1/checkout/create-order-minimal` with the buyer phone.
2. `POST /v1/checkout/wallet-payment` to push USSD/STK to that number.
3. Selcom calls `/webhooks/selcom/` when the customer pays.
4. The waiting page also polls `GET /v1/checkout/order-status`.

The webhook URL must be a public HTTPS address Selcom can reach.

## Notes

- Project package is `awayvideos` (valid Python package name — no spaces).
- Video files are stored in `media/videos/`.
- SQLite is used for simplicity.
- Change the demo admin password before any public deployment.
