import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str = ""
    admin_ids: list[int] = field(default_factory=list)
    channel_id: int = 0
    channel_username: str = ""
    db_url: str = "sqlite+aiosqlite:///data/konkurs.db"

    @classmethod
    def from_env(cls) -> "Config":
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            admin_ids=admin_ids,
            channel_id=int(os.getenv("CHANNEL_ID", "0")),
            channel_username=os.getenv("CHANNEL_USERNAME", ""),
            db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///data/konkurs.db"),
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids
