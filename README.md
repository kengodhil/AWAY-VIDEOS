# AWAY VIDEOS Reel

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
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

Demo admin login:

- Username: `admin`
- Password: `admin123`

With `SELCOM_MOCK=true` (the default), the payment screen has a demo confirm button so you can test without live Selcom keys.

## Live Selcom setup

Ask Selcom for an API key, API secret, and vendor/till ID. Put them in `.env`:

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

- Video files are stored in `media/videos/`.
- SQLite is used for simplicity.
- Change the demo admin password before any public deployment.
