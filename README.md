# Konkurs Telegram Bot 🏆

Professional darajadagi Telegram konkurs bot loyihasi. Ushbu bot orqali siz o'z kanallaringiz va guruhlaringizda adolatli, shaffof va yuqori darajada avtomatlashtirilgan tanlovlar o'tkazishingiz mumkin.

## ✨ Yangi va Asosiy Imkoniyatlar

- **Ehtimollik asosida g'olib tanlash (Weighted Random)** — Referal tizimi orqali ko'proq do'stlarni taklif qilgan foydalanuvchilarning yutish ehtimoli avtomatik ravishda oshadi.
- **To'liq Ro'yxatdan o'tish tizimi** — Foydalanuvchilardan Ism, Familiya, Telefon raqami va Yashash joyini so'rab olish (FSM asosida).
- **Media qo'llab-quvvatlash** — Konkurslarga rasm yoki video biriktirish, natijalarni media bilan e'lon qilish.
- **Multi-Media Broadcast** — Adminlar barcha foydalanuvchilarga bir vaqtning o'zida bir nechta xabarlarni (matn, rasm, video) tarqata oladi.
- **Majburiy Obuna (Force Subscription)** — Botdan foydalanish yoki konkursda qatnashish uchun belgilangan kanallarga a'zo bo'lish sharti.
- **Media ID Detektori** — Admin botga media fayl yuborganda, bot uning `file_id`sini darhol qaytaradi (web-panel uchun qulaylik).
- **Web Admin Dashboard** — FastAPI asosidagi zamonaviy boshqaruv paneli (Statistika, CRM, Konkurs boshqaruvi).
- **CRM Tizimi** — Bizneslar, mijozlar va teglar bilan ishlash imkoniyati.

## 🛠 Texnologiyalar

- **Python 3.11+**
- **Aiogram 3.x** — Telegram bot uchun asinxron kutubxona
- **FastAPI** — Web admin panel uchun
- **SQLAlchemy** — ORM (Object Relational Mapping)
- **SQLite** — Ma'lumotlar bazasi sifatida (production uchun oson ko'chiriladigan)
- **Uvicorn** — ASGI server
- **Jinja2** — Web shablonlar uchun

## 📂 Loyiha Tuzilmasi

```text
├── app/
│   ├── db/              # Ma'lumotlar bazasi modellari va engine
│   ├── handlers/        # Bot buyruqlari (admin, start, registration, user)
│   ├── keyboards/       # Inline va Reply tugmalar
│   ├── middlewares/     # Bot middlewarelari (DB session)
│   ├── services/        # Biznes mantiqi (contest, subscription, user)
│   └── utils/           # Yordamchi funksiyalar (formatting)
├── data/                # Ma'lumotlar bazasi fayli (.db)
├── web/
│   ├── static/          # CSS va JS fayllar
│   ├── templates/       # HTML shablonlar
│   ├── app.py           # FastAPI konfiguratsiyasi
│   └── routes.py        # Web marshrutlar
├── main.py              # ASOSIY ISHGA TUSHIRISH FAYLI (Bot + Web)
├── render.yaml          # Render.com uchun deployment sozlamalari
└── requirements.txt     # Kerakli kutubxonalar
```

## 🚀 Ishga Tushirish

1. **Repozitoriyani yuklab oling:**
   ```bash
   git clone https://github.com/JahongirObloqulov/konkurs-bot.git
   cd konkurs-bot
   ```

2. **Virtual muhit yaratish va kutubxonalarni o'rnatish:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **.env faylini sozlang:**
   `.env.example` faylini `.env` deb nomlang va o'zingizning ma'lumotlaringizni kiriting:
   ```env
   BOT_TOKEN=Sizning_Bot_Tokeningiz
   ADMIN_IDS=1234567,8901234
   WEB_SECRET_KEY=ixtiyoriy_murakkab_kod
   ```

4. **Loyiha ishga tushiring:**
   ```bash
   python main.py
   ```
   *Bot va Web panel (port 8000) bir vaqtda ishga tushadi.*

## 📈 Statistika va Boshqaruv

Botga kirganingizda `/start` buyrug'i orqali admin bo'lsangiz, maxsus admin menyusi chiqadi. Web-panelga kirish uchun esa brauzerda `http://localhost:8000/dashboard` manziliga kiring (login/parol `.env` yoki sozlamalarda ko'rsatilgan).

## 🛡 Xavfsizlik

- Barcha admin amallari ID orqali tekshiriladi.
- Web-panel sessiya va xavfsiz cookie-fayllar orqali himoyalangan.
- Ma'lumotlar bazasi SQLite orqali local holda saqlanadi.

---
Loyiha ishlab chiqish jarayonida: **Antigravity AI Coding Assistant** tomonidan yaratildi.