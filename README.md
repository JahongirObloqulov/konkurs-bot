# Konkurs Telegram Bot 🏆 (Enterprise Edition)

Professional va yuqori darajada avtomatlashtirilgan Telegram konkurs bot loyihasi. Ushbu tizim orqali siz o'z kanallaringiz va guruhlaringizda adolatli, shaffof va zamonaviy tanlovlar o'tkazishingiz, shuningdek, mukammal boshqaruv paneliga ega bo'lishingiz mumkin.

## 🚀 Eng Yangi "Enterprise" Imkoniyatlar

Ushbu loyiha so'nggi yangilanishlar bilan yanada kuchaytirildi:

- **🤖 AI Yordamchi (Gemini/OpenRouter)**:
    - **Adminlar uchun:** Xabar matnlarini aqlli tarzda generatsiya qilish.
    - **Foydalanuvchilar uchun:** Bot ichida jonli AI chat orqali yordam olish.
- **📊 Interaktiv Analitika**: Admin panelda foydalanuvchilar o'sish grafigi va turli statistik ma'lumotlar vizual tarzda (`Chart.js`) ko'rsatiladi.
- **📜 Audit Logs (Amallar Tarixi)**: Adminlar tomonidan bajarilgan barcha muhim amallar (eksport, g'oliblarni aniqlash, media qo'shish) tarixda saqlanadi.
- **⚡️ Real-time Bildirishnomalar**: Dashboard-da yangi foydalanuvchilar qo'shilishi jonli (SSE texnologiyasi) tarzda ko'rinadi.
- **🖼 Media Manager**: Botdagi barcha File ID larni boshqarish uchun markaziy galereya.
- **📑 Eksport Tizimi**: Barcha statistik ma'lumotlar, ishtirokchilar va mijozlar ro'yxatini bir tugma bilan **Excel** yoki **PDF** formatida yuklab olish.

## ✨ Boshqa Asosiy Imkoniyatlar

- **Ehtimollik asosida g'olib tanlash (Weighted Random)** — Referal soniga qarab yutish imkoniyatini oshirish.
- **To'liq Ro'yxatdan o'tish tizimi** — Ism, Familiya, Telefon va Manzilni yig'ish (FSM).
- **Majburiy Obuna (Force Subscription)** — Kanallarga a'zo bo'lish shartini tekshirish.
- **CRM Tizimi** — Bizneslar va mijozlarni boshqarish uchun qulay platforma.

## 🛠 Texnologiyalar

- **Python 3.11+**, **Aiogram 3.x**
- **FastAPI**, **SQLAlchemy** (Asinxron)
- **Chart.js** (Vizualizatsiya)
- **OpenRouter AI** (LLM integratsiyasi)
- **SQLite** (Ma'lumotlar bazasi)
- **Jinja2** & **Tailwind CSS** (Web UI)

## 📂 Loyiha Tuzilmasi

```text
├── app/
│   ├── db/              # Modellar va engine
│   ├── handlers/        # Bot buyruqlari (admin, user, registration, AI)
│   ├── services/        # Biznes mantiqi (AI, Audit, Export, Contest)
│   └── utils/           # Formatting va yordamchi funksiyalar
├── web/
│   ├── static/          # CSS va vizual elementlar
│   ├── templates/       # HTML shablonlar (Admin panel)
│   ├── app.py           # FastAPI asosi
│   └── routes.py        # Web marshrutlar va API
├── main.py              # ASOSIY ISHGA TUSHIRISH (Bot + Web)
└── requirements.txt     # Kerakli kutubxonalar
```

## 🚀 Ishga Tushirish

1. **Repozitoriyani yuklab oling:**
   ```bash
   git clone https://github.com/JahongirObloqulov/konkurs-bot.git
   cd konkurs-bot
   ```

2. **Virtual muhit va kutubxonalar:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **.env faylini sozlang:**
   `.env.example`ni `.env`ga o'zgartiring va quyidagilarni kiriting:
   ```env
   BOT_TOKEN=Sizning_Bot_Tokeningiz
   ADMIN_IDS=1234567
   OPENROUTER_API_KEY=Sizning_API_kalitingiz
   OPENROUTER_MODEL=openrouter/free
   ```

4. **Ishga tushirish:**
   ```bash
   python main.py
   ```

## 📈 Boshqaruv
Web-panelga kirish: `http://localhost:8000/dashboard` (Login: admin, Parol: admin123).

---
Loyiha ishlab chiqish jarayonida: **Antigravity AI Coding Assistant** tomonidan modernizatsiya qilindi.