"""
config.py

Чтение и запись config.txt с настройками отображения: язык интерфейса
и (опционально) маленькая картинка/подпись на карточке Discord.

Имя пользователя VK больше не требуется: данные о треке теперь
приходят от браузерного расширения (vkrpc-extension), а не из
отдельного запроса к странице конкретного профиля.
"""

import locale
import os

from paths import resource_path

CONFIG_PATH = resource_path("config.txt")

DEFAULT_LARGE_IMAGE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/"
    "VK_Compact_Logo_%282021-present%29.svg/2048px-VK_Compact_Logo_%282021-present%29.svg.png"
)
# По умолчанию маленькая картинка не задана — раньше тут был чужой
# CDN-гиф и подпись "ivan", теперь пользователь сам решает.
DEFAULT_SMALL_IMAGE_URL = ""
DEFAULT_SMALL_TEXT = "VK Music"


def _detect_default_lang():
    """Best-effort угадывание языка по системной локали — используется
    только в неинтерактивном режиме (например, трей-версия без
    консоли, где input() спросить не у кого)."""
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""
    return "ru" if loc.lower().startswith("ru") else "en"


def load_config(interactive=True):
    """Читает config.txt. Если файла нет — в интерактивном режиме
    спрашивает язык в консоли, иначе определяет его по системной
    локали без вопросов (нужно для запуска без консоли — трей/exe).
    Возвращает dict с lang/small_image/small_text."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.read().splitlines()]
        if not lines or not lines[0]:
            raise ValueError(
                "config.txt повреждён или пуст, удали его и запусти скрипт заново."
            )
        lang = lines[0].lower() if lines[0].lower() in ("ru", "en") else "en"
        small_image = lines[1] if len(lines) > 1 else DEFAULT_SMALL_IMAGE_URL
        small_text = lines[2] if len(lines) > 2 else DEFAULT_SMALL_TEXT
        return {"lang": lang, "small_image": small_image, "small_text": small_text}

    if interactive:
        lang = input("Выберите язык [RU/EN]: ").strip().lower()
        lang = lang if lang in ("ru", "en") else "en"
    else:
        lang = _detect_default_lang()

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(f"{lang}\n{DEFAULT_SMALL_IMAGE_URL}\n{DEFAULT_SMALL_TEXT}\n")

    return {
        "lang": lang,
        "small_image": DEFAULT_SMALL_IMAGE_URL,
        "small_text": DEFAULT_SMALL_TEXT,
    }
