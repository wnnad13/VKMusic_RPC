"""
tray.py

Точка входа для фонового режима: без окна консоли, с иконкой в трее.
Текущий трек показывается во всплывающей подсказке иконки; через
контекстное меню можно открыть лог или выйти. Использует ту же логику
опроса/обновления Discord Presence, что и main.py (через
presence_loop.PresenceLoop) — отличается только тем, как показывается
результат.

Собирается в отдельный .exe через PyInstaller — этот
файл и есть точка входа для такой сборки (pyinstaller --onefile --noconsole --name "VKM RPC" tray.py).
"""

import os
import threading

import pystray
from PIL import Image, ImageDraw

from config import load_config
from discord_presence import DiscordPresence
from local_server import TrackStore, start_server
from logger import log, LOG_PATH
from presence_loop import PresenceLoop

DISCORD_CLIENT_ID = "1546931297824276580"
SERVER_PORT = 39285

_running = True


def create_icon_image():
    """Рисует простую иконку прямо в коде — не требует отдельного
    файла картинки, который пришлось бы отдельно копировать при сборке."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, size - 2, size - 2), fill=(88, 101, 242, 255))
    draw.text((24, 18), "V", fill=(255, 255, 255, 255))
    return img


def open_log(icon, item):
    try:
        os.startfile(os.path.abspath(LOG_PATH))
    except Exception as exc:
        log(f"Не удалось открыть лог из трея: {exc}")


def quit_app(icon, item):
    global _running
    _running = False
    icon.stop()


def worker(icon, config, lang):
    presence = DiscordPresence(DISCORD_CLIENT_ID)
    try:
        presence.connect()
    except Exception as exc:
        log(f"Не удалось подключиться к Discord: {exc}")
        icon.title = "VKM RPC — нет связи с Discord"
        return

    store = TrackStore()
    start_server(store, port=SERVER_PORT)

    loop = PresenceLoop(store, presence, config, lang)
    icon.title = "VKM RPC — жду музыку" if lang == "ru" else "VKM RPC — waiting for music"

    while _running:
        track, messages = loop.wait_and_update(timeout=10)
        for message in messages:
            log(message)
        if track:
            title = f"{track['title']} — {track['artist']}"
            icon.title = title[:127]  # Windows ограничивает длину подсказки трея


def main():
    config = load_config(interactive=False)  # нет консоли — спрашивать язык не у кого
    lang = config["lang"]

    icon = pystray.Icon(
        "vkm_rpc",
        icon=create_icon_image(),
        title="VKM RPC",
        menu=pystray.Menu(
            pystray.MenuItem("Открыть лог" if lang == "ru" else "Open log", open_log),
            pystray.MenuItem("Выход" if lang == "ru" else "Quit", quit_app),
        ),
    )

    thread = threading.Thread(target=worker, args=(icon, config, lang), daemon=True)
    thread.start()

    icon.run()


if __name__ == "__main__":
    main()
