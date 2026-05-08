import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

(TEMPLATES_DIR / "layouts").mkdir(exist_ok=True)
(TEMPLATES_DIR / "pages").mkdir(exist_ok=True)
(TEMPLATES_DIR / "components").mkdir(exist_ok=True)