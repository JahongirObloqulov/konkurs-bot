import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str = ""
    admin_ids: list[int] = field(default_factory=list)
    required_chats: list[dict] = field(default_factory=list)
    db_url: str = "sqlite+aiosqlite:///data/konkurs.db"

    @classmethod
    def from_env(cls) -> "Config":
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

        required_chats_str = os.getenv("REQUIRED_CHATS", "")
        required_chats = []
        if required_chats_str:
            for chat in required_chats_str.split(";"):
                chat = chat.strip()
                if chat:
                    parts = chat.split(",")
                    chat_id = int(parts[0].strip())
                    chat_username = parts[1].strip() if len(parts) > 1 else ""
                    chat_type = parts[2].strip() if len(parts) > 2 else "channel"
                    required_chats.append({
                        "id": chat_id,
                        "username": chat_username,
                        "type": chat_type
                    })

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            admin_ids=admin_ids,
            required_chats=required_chats,
            db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///data/konkurs.db"),
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    def get_chat_by_id(self, chat_id: int) -> dict | None:
        for chat in self.required_chats:
            if chat["id"] == chat_id:
                return chat
        return None