import httpx
import os
import logging

logger = logging.getLogger(__name__)

async def get_ai_response(prompt: str, user_id: int = None) -> str:
    """
    Calls OpenRouter to get an AI response for the bot user.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    
    if not api_key:
        return "⚠️ AI xizmati vaqtinchalik o'chirilgan (API key topilmadi)."
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/JahongirObloqulov/konkurs-bot",
    }
    
    system_instruction = (
        "Siz Konkurs Botining yordamchisisiz. Foydalanuvchilarga botdan foydalanish, "
        "konkurslarda qatnashish va boshqa savollar bo'yicha yordam berasiz. "
        "Javoblaringiz qisqa, do'stona va o'zbek tilida bo'lsin."
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            # Simple retry/fallback for 429/404
            if response.status_code in [404, 429]:
                payload["model"] = "openrouter/free"
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

        if response.status_code != 200:
            logger.error(f"OpenRouter Error: {response.text}")
            return "❌ AI xizmatida texnik nosozlik yuz berdi. Birozdan so'ng urinib ko'ring."
            
        res_data = response.json()
        return res_data['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        logger.error(f"AI Service Exception: {e}")
        return "❌ Kechirasiz, hozirda javob bera olmayman."
