# SVOS — خطوات الرفع على Railway

## الخطوة 1 — إعداد .env

```bash
cp .env.example .env
# افتح .env وأضف مفاتيحك
```

المفاتيح الإلزامية للتشغيل الأساسي:
- `ANTHROPIC_API_KEY` — الوكلاء لا يعملون بدونه
- `SVOS_MASTER_KEY` — كلمة سر قوية أنت تختارها
- `SVOS_API_KEY` — كلمة سر قوية أنت تختارها

---

## الخطوة 2 — رفع على Railway

1. اذهب إلى [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. اختر `putxq/svos`
4. في Variables أضف كل متغيرات `.env`
5. Railway يرفع تلقائياً من Dockerfile

---

## الخطوة 3 — Domain

في Railway:
- Settings → Networking → Generate Domain
- أو أضف Custom Domain الخاص بك

---

## الخطوة 4 — تحقق من التشغيل

```bash
curl https://your-domain.railway.app/health
# يرجع: {"status":"ok","svos":"v1.0"}

curl https://your-domain.railway.app/auth/ping
# يرجع: {"pong":true}
```

---

## الخطوة 5 — تفعيل الأدوات (اختياري)

| الأداة | المفاتيح المطلوبة |
|--------|------------------|
| Email | SMTP_HOST, SMTP_USER, SMTP_PASS |
| WhatsApp | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN |
| Payments | STRIPE_SECRET_KEY أو MOYASAR_API_KEY |

---

## تشغيل محلي

```bash
pip install -r requirements.txt
cp .env.example .env
# أضف ANTHROPIC_API_KEY في .env
uvicorn main:app --reload --port 8000
```

ثم افتح: http://localhost:8000/dashboard
