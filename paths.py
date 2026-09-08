"""
paths.py

Определяет папку, где реально лежит запущенный скрипт или собранный
.exe — чтобы config.txt и vkrpc.log всегда создавались рядом с ним,
а не там, откуда случайно была запущена программа. Это особенно важно
для автозапуска из папки "Автозагрузка" Windows, где рабочая
директория процесса не гарантирована и часто не совпадает с папкой,
где реально лежит exe.
"""

import os
import sys


def base_dir():
    if getattr(sys, "frozen", False):
        # Собранный PyInstaller-ом .exe — sys.executable указывает
        # на сам exe-файл.
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(filename):
    return os.path.join(base_dir(), filename)
