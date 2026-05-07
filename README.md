# Konkurs Telegram Bot

Telegram orqali konkurslar (tanlovlar) tashkil qilish uchun bot. Admin konkurs yaratadi, foydalanuvchilar ishtirok etadi, bot tasodifiy g'oliblarni tanlaydi.

## Imkoniyatlar

- **Konkurs yaratish** — Admin panel orqali yangi konkurs e'lon qilish
- **Rasm/Video biriktirish** — Konkursga media fayl qo'shish (rasm, video, GIF)
- **Kanalga obuna tekshirish** — Ishtirok etishdan oldin kanalga obuna bo'lish sharti
- **Vaqt limiti** — Konkursni avtomatik tugatish (1 soatdan 72 soatgacha yoki custom)
- **Referral tizimi** — Do'stlarni taklif qilish, taklif havolasi orqali ishtirok etish
- **Inline rejim** — Botni inline rejimda ishlatib konkurslarni ulashish
- **Tasodifiy g'olib tanlash** — Ishtirokchilar orasidan random g'oliblarni aniqlash
- **Natijalarni e'lon qilish** — G'oliblarni bot orqali e'lon qilish
- **Broadcast** — Barcha foydalanuvchilarga xabar yuborish
- **CSV Export** — Ishtirokchilar ro'yxatini CSV formatda yuklab olish
- **Statistika** — Foydalanuvchilar, konkurslar va ishtirokchilar statistikasi

## Texnologiyalar

- **Python 3.11+**
- **aiogram 3.x** — Asinxron Telegram Bot framework
- **SQLAlchemy 2.x** — ORM (asinxron rejimda)
- **aiosqlite** — SQLite asinxron driver
- **APScheduler** — Vaqt limiti bilan konkurslarni avtomatik tugatish
- **python-dotenv** — Muhit o'zgaruvchilarini boshqarish

## O'rnatish

### 1. Repositoryni klonlash

```bash
git clone https://github.com/JahongirObloqulov/konkurs-bot.git
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
4. **Do'stlarni taklif qilish** — Referral havola orqali do'stlarni taklif qilish
5. **Mening ishtiroklarim** — O'z ishtiroklaringizni ko'rish
6. **Inline rejim** — `@bot_username` yozib konkurslarni boshqa chatlarga ulashish

### Admin uchun

1. `/start` — Admin panelga kirish
2. **Konkurs yaratish** — Yangi konkurs yaratish (nom, tavsif, sovg'a, rasm/video, g'oliblar soni, vaqt limiti)
3. **Barcha konkurslar** — Barcha konkurslarni boshqarish
4. **G'oliblarni tanlash** — Tasodifiy g'oliblarni tanlash
5. **CSV Export** — Ishtirokchilar ro'yxatini CSV formatda yuklab olish
6. **Broadcast** — Barcha foydalanuvchilarga xabar yuborish
7. **Statistika** — Bot statistikasini ko'rish

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
    │   └── models.py       # Database modellari (Contest, Participant, Winner, User, Referral)
    ├── handlers/
    │   ├── start.py        # /start buyrug'i + referral deep link
    │   ├── user.py         # Foydalanuvchi handlerlari
    │   ├── admin.py        # Admin handlerlari (yaratish, broadcast, CSV)
    │   └── inline.py       # Inline query handler
    ├── keyboards/
    │   └── inline.py       # Inline tugmalar
    ├── middlewares/
    │   └── db_middleware.py # Database middleware
    ├── services/
    │   ├── contest_service.py      # Konkurs servisi
    │   ├── scheduler_service.py    # Vaqt limiti scheduler
    │   ├── subscription_service.py # Obuna tekshirish
    │   └── user_service.py         # Foydalanuvchi servisi
    └── utils/
        └── formatting.py   # Formatlash helper funksiyalari
```

## Yangi funksiyalar

### Rasm/Video biriktirish
Konkurs yaratishda rasm, video yoki GIF biriktirish mumkin. Media fayl konkurs tafsilotlarida ko'rsatiladi.

### Vaqt limiti
Konkurs yaratishda vaqt limiti belgilash mumkin (1, 6, 12, 24, 48, 72 soat yoki custom). Vaqt tugaganda konkurs avtomatik tugatiladi va g'oliblar tanlanadi.

### Referral tizimi
Ishtirokchilar o'z referral havolasini do'stlariga yuborishlari mumkin. Havola orqali qo'shilgan foydalanuvchilar referral hisobiga qo'shiladi. Admin ishtirokchilar ro'yxatida referral sonini ko'rishi mumkin.

### Inline rejim
Bot inline rejimda ishlaydi. Foydalanuvchilar `@bot_username` yozib faol konkurslarni boshqa chatlarga ulashishlari mumkin. Har bir konkurs uchun referral havola avtomatik generatsiya qilinadi.

### Broadcast
Admin barcha foydalanuvchilarga matn, rasm yoki video xabar yuborishi mumkin. Yuborish jarayoni real-time kuzatiladi.

### CSV Export
Admin ishtirokchilar ro'yxatini CSV formatda yuklab olishi mumkin. Fayl foydalanuvchi ID, username, ism va referral ma'lumotlarini o'z ichiga oladi.

## Litsenziya

MIT License
