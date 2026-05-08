# Konkurs Telegram Bot

Telegram orqali konkurslar (tanlovlar) tashkil qilish uchun bot.
Admin konkurs yaratadi, foydalanuvchilar ishtirok etadi, bot tasodifiy g'oliblarni tanlaydi.

## Imkoniyatlar

- **Konkurs yaratish** — Admin panel orqali yangi konkurs e'lon qilish
- **Kanalga obuna tekshirish** — Ishtirok etishdan oldin kanalga obuna bo'lish sharti
- **Ishtirokchilarni boshqarish** — Ro'yxatga olish va kuzatish
- **Tasodifiy g'olib tanlash** — Ishtirokchilar orasidan random g'oliblarni aniqlash
- **Natijalarni e'lon qilish** — G'oliblarni bot orqali e'lon qilish
- **Statistika** — Foydalanuvchilar, konkurslar va ishtirokchilar statistikasi
- **Web Admin Dashboard** — FastAPI asosidagi veb interfeys (CRM bilan)
- **CRM** — Bizneslar, mijozlar, interaksiyalar va teglar bilan ishlash

## Texnologiyalar

- **Python 3.11+**
- **aiogram 3.x** — Asinxron Telegram Bot framework
- **FastAPI** — Web admin panel uchun
- **SQLAlchemy 2.x** — ORM (asinxron rejimda)
- **PostgreSQL** — Render.com da ishlatish uchun (SQLite lokalda)
- **Jinja2** — Veb shablonlar
- **Chart.js** — Dashboard diagrammalar

## Lokal O'rnatish

### 1. Repositoryni klonlash

```bash
git clone https://github.com/your-username/konkurs-bot.git
cd konkurs-bot
```

### 2. Virtual muhit yaratish

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Muhit sozlamalari

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather dan olingan bot tokeni |
| `ADMIN_IDS` | Admin foydalanuvchilarning Telegram ID lari (vergul bilan) |
| `DB_URL` | Ma'lumotlar bazasi URL (standart: sqlite) |
| `WEB_SECRET_KEY` | JWT tokenlar uchun maxfiy kalit |
| `WEB_ADMIN_USERNAME` | Admin panel username |
| `WEB_ADMIN_PASSWORD` | Admin panel password |

### 5. Ishga tushirish

**Botni ishga tushirish:**
```bash
python bot.py
```

**Web admin panelni ishga tushirish:**
```bash
python run_web.py
```

Brauzerda: http://127.0.0.1:8000

## Render.com ga Deploy Qilish

### 1. Repositoryni GitHub ga push qiling

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/konkurs-bot.git
git push -u origin main
```

### 2. Render.com da yangi Blueprint yarating

1. [Render.com](https://dashboard.render.com) saytiga kiring
2. **New +** → **Blueprint** ni tanlang
3. GitHub repoyingizni ulang
4. `render.yaml` fayli avtomatik topiladi
5. **Apply** tugmasini bosing

### 3. Environment o'zgaruvchilarni sozlash

Render blueprint quyidagi o'zgaruvchilarni so'rashi kerak. Ularni qo'lda kiritasiz:

| Variable | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather dan olingan bot token |
| `ADMIN_IDS` | Admin Telegram ID lari (vergul bilan) |
| `WEB_SECRET_KEY` | Maxfiy kalit (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `WEB_ADMIN_USERNAME` | Admin panel login |
| `WEB_ADMIN_PASSWORD` | Admin panel password |

Render avtomatik ravishda:
- 1 GB disk (`/data`) yaratadi — SQLite ma'lumotlar bazasi shu yerda saqlanadi
- Web serviceni (`konkurs-bot`) ishga tushiradi
- Bot background rejimda, web esa foreground da ishlaydi

### Render servislari

| Service | Type | Izoh |
|---|---|---|
| `konkurs-bot` | Web | FastAPI admin panel + Telegram bot birgalikda |
| Disk (`/data`) | Persistent | SQLite DB saqlanadi, restartda o'chmaydi |

## Loyiha strukturasi

```
konkurs-bot/
├── bot.py                  # Bot asosiy fayli
├── run_web.py              # Web serverni ishga tushirish
├── start.sh                # Render ishga tushirish skripti
├── render.yaml             # Render Blueprint konfigi
├── requirements.txt        # Kutubxonalar
├── .env.example            # Muhit sozlamalari namunasi
├── .gitignore
├── README.md
├── app/
│   ├── config.py           # Konfiguratsiya
│   ├── db/
│   │   ├── engine.py       # Database ulanish
│   │   └── models.py       # Database modellari
│   ├── handlers/
│   │   ├── start.py        # /start buyrug'i
│   │   ├── user.py         # Foydalanuvchi handlerlari
│   │   └── admin.py        # Admin handlerlari
│   ├── keyboards/
│   │   └── inline.py       # Inline tugmalar
│   ├── middlewares/
│   │   └── db_middleware.py # Database middleware
│   ├── services/
│   │   ├── contest_service.py      # Konkurs servisi
│   │   ├── subscription_service.py # Obuna tekshirish
│   │   ├── settings_service.py     # Sozlamalar
│   │   ├── crm_service.py          # CRM servisi
│   │   └── user_service.py         # Foydalanuvchi servisi
│   └── utils/
├── web/
│   ├── app.py              # FastAPI ilova
│   ├── routes.py           # Web marshrutlar
│   ├── crm_routes.py       # CRM marshrutlar
│   ├── static/             # Statik fayllar
│   └── templates/          # Jinja2 shablonlar
│       ├── layouts/
│       │   └── base.html
│       └── pages/
│           ├── login.html
│           ├── dashboard.html
│           ├── contests.html
│           ├── contest_detail.html
│           ├── contest_form.html
│           ├── chats.html
│           ├── users.html
│           ├── user_detail.html
│           └── crm/
│               ├── dashboard.html
│               ├── businesses.html
│               ├── business_detail.html
│               ├── business_form.html
│               ├── customers.html
│               ├── customer_detail.html
│               ├── customer_form.html
│               ├── interaction_form.html
│               └── tags.html
```

## Litsenziya

MIT License