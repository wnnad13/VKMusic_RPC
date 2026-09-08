"""
logger.py

Простой файловый лог для диагностики проблем с обложками треков:
что случилось — обложка отсутствовала на странице VK, её ссылка
оказалась длиннее лимита Discord, или сам Discord отклонил уже
готовое обновление. Пишет в vkrpc.log рядом со скриптом/exe (не там,
откуда его запустили), дописывая в конец файла.
"""

import datetime

from paths import resource_path

LOG_PATH = resource_path("vkrpc.log")


def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # логирование не должно ронять основной скрипт
