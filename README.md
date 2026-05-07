# Konkurs Telegram Bot

Telegram orqali konkurslar (tanlovlar) tashkil qilish uchun bot. Admin konkurs yaratadi, foydalanuvchilar ishtirok etadi, bot tasodifiy g'oliblarni tanlaydi.

## Imkoniyatlar

- **Konkurs yaratish** — Admin panel orqali yangi konkurs e'lon qilish
- **Kanalga obuna tekshirish** — Ishtirok etishdan oldin kanalga obuna bo'lish sharti
- **Ishtirokchilarni boshqarish** — Ro'yxatga olish va kuzatish
- **Tasodifiy g'olib tanlash** — Ishtirokchilar orasidan random g'oliblarni aniqlash
- **Natijalarni e'lon qilish** — G'oliblarni bot orqali e'lon qilish
- **Statistika** — Foydalanuvchilar, konkurslar va ishtirokchilar statistikasi

## Texnologiyalar

- **Python 3.11+**
- **aiogram 3.x** — Asinxron Telegram Bot framework
- **SQLAlchemy 2.x** — ORM (asinxron rejimda)
- **aiosqlite** — SQLite asinxron driver
- **python-dotenv** — Muhit o'zgaruvchilarini boshqarish

## O'rnatish

### 1. Repositoryni klonlash

```bash
git clone https://github.com/your-username/konkurs-bot.git
cd konkurs-bot
```

### 2. Virtual muhit yaratish

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Muhit sozlamalari

`.env.example` faylidan `.env` fayl yarating:

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
CHANNEL_ID=-1001234567890
CHANNEL_USERNAME=@your_channel
```

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather dan olingan bot tokeni |
| `ADMIN_IDS` | Admin foydalanuvchilarning Telegram ID lari (vergul bilan ajratilgan) |
| `CHANNEL_ID` | Obuna tekshirish uchun kanal ID si |
| `CHANNEL_USERNAME` | Kanal username (@ bilan) |

### 5. Botni ishga tushirish

```bash
python bot.py
```

## Foydalanish

### Foydalanuvchi uchun

1. `/start` — Botni ishga tushirish
2. **Faol konkurslar** — Hozirda davom etayotgan konkurslarni ko'rish
3. **Ishtirok etish** — Konkursga qo'shilish (kanalga obuna shart bo'lishi mumkin)
4. **Mening ishtiroklarim** — O'z ishtiroklaringizni ko'rish

### Admin uchun

1. `/start` — Admin panelga kirish
2. **Konkurs yaratish** — Yangi konkurs yaratish (nom, tavsif, sovg'a, g'oliblar soni)
3. **Barcha konkurslar** — Barcha konkurslarni boshqarish
4. **G'oliblarni tanlash** — Tasodifiy g'oliblarni tanlash
5. **Statistika** — Bot statistikasini ko'rish

## Loyiha strukturasi

```
konkurs-bot/
├── bot.py                  # Asosiy fayl
├── requirements.txt        # Kutubxonalar
├── .env.example           # Muhit sozlamalari namunasi
├── .gitignore
├── README.md
└── app/
    ├── config.py           # Konfiguratsiya
    ├── db/
    │   ├── engine.py       # Database ulanish
    │   └── models.py       # Database modellari
    ├── handlers/
    │   ├── start.py        # /start buyrug'i
    │   ├── user.py         # Foydalanuvchi handlerlari
    │   └── admin.py        # Admin handlerlari
    ├── keyboards/
    │   └── inline.py       # Inline tugmalar
    ├── middlewares/
    │   └── db_middleware.py # Database middleware
    ├── services/
    │   ├── contest_service.py      # Konkurs servisi
    │   ├── subscription_service.py # Obuna tekshirish
    │   └── user_service.py         # Foydalanuvchi servisi
    └── utils/
```

## Litsenziya

MIT License
