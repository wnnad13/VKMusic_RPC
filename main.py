"""
main.py

Консольная точка входа: поднимает локальный сервер, ждёт обновления
от браузерного расширения (vkrpc-extension) и обновляет Discord Rich
Presence, показывая живой статус в консоли. Для фонового режима без
окна консоли и с иконкой в трее используй tray.py вместо этого файла.
"""

import os
import sys
import time

from colorama import Fore

from config import load_config
from discord_presence import DiscordPresence
from local_server import TrackStore, start_server
from presence_loop import PresenceLoop

DISCORD_CLIENT_ID = "1546931297824276580"
SERVER_PORT = 39285

VK_TIMEOUT_SECONDS = 10  # сколько секунд без данных считать VK-соединение потерянным

LOGO = r"""
 _    ____ __ __  ___   ____  ____  ______
| |  / / //_//  |/  /  / __ \/ __ \/ ____/
| | / / ,<  / /|_/ /  / /_/ / /_/ / /     
| |/ / /| |/ /  / /  / _, _/ ____/ /___   
|___/_/ |_/_/  /_/  /_/ |_/_/    \____/   
"""


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def status_mark(state):
    """state: True (ок, зелёный), False (проблема, красный) или None (ждём, жёлтый).
    Используем чистый ASCII вместо Unicode-символов ✓/✗ — не все
    шрифты консоли Windows их поддерживают и могут показывать
    "квадратик"-заглушку вместо значка."""
    if state is True:
        return f"{Fore.GREEN}[OK]{Fore.WHITE}"
    if state is False:
        return f"{Fore.RED}[--]{Fore.WHITE}"
    return f"{Fore.YELLOW}[..]{Fore.WHITE}"


def vk_state(loop):
    if loop.last_data_at is None:
        return None
    return (time.monotonic() - loop.last_data_at) < VK_TIMEOUT_SECONDS


def render(loop, current_track, lang):
    """Перерисовывает весь экран заново: лого и строки статуса
    остаются визуально на том же месте (просто перерисовываются
    каждый раз), а не печатаются новым блоком вниз."""
    clear()
    print(Fore.CYAN + LOGO + Fore.WHITE)

    vk_label = "Подключение VK" if lang == "ru" else "VK Connection"
    discord_label = "Подключение Discord" if lang == "ru" else "Discord Connection"
    print(f"{status_mark(vk_state(loop))} {vk_label}")
    print(f"{status_mark(loop.discord_ok)} {discord_label}")
    print()

    if current_track:
        print(f"{Fore.GREEN}♪ {current_track['title']}{Fore.WHITE}")
        print(f"{Fore.CYAN}└ {Fore.WHITE}{current_track['artist']}")


def main():
    config = load_config()
    lang = config["lang"]

    presence = DiscordPresence(DISCORD_CLIENT_ID)
    print("Подключаюсь к Discord..." if lang == "ru" else "Connecting to Discord...")
    presence.connect()

    store = TrackStore()
    start_server(store, port=SERVER_PORT)

    loop = PresenceLoop(store, presence, config, lang)
    current_track = None
    render(loop, current_track, lang)

    while True:
        track, messages = loop.wait_and_update(timeout=10)
        if track:
            current_track = track
        render(loop, current_track, lang)
        for message in messages:
            print(Fore.YELLOW + message + Fore.WHITE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
