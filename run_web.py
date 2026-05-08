"""
Web admin panel uchun ishga tushirish skripti.
Bot bilan birga ishlatish uchun alohida terminalda ishga tushiring.

Usage:
    python run_web.py
"""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))
    
    print(f"🌐 Web admin panel: http://{host}:{port}")
    print("📝 Login: admin / admin123 (.env faylidan o'zgartiring)")
    
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=True,
    )