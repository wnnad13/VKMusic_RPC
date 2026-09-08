"""
discord_presence.py

Тонкая обёртка над pypresence.Presence, чтобы main.py не занимался
деталями подключения к Discord и переподключением при обрыве связи
(например, если Discord перезапустили или закрыли во время работы
скрипта). Любая ошибка при отправке обновления (в том числе от самого
Discord — например, если он отклонил картинку) поднимается как
PresenceUpdateError, а не как случайное исключение pypresence, чтобы
main.py мог поймать её одним понятным типом и не падать целиком.
"""

import time

from pypresence import Presence, PipeClosed, DiscordNotFound


class PresenceUpdateError(Exception):
    """Не удалось отправить обновление в Discord даже после
    переподключения. Не критично — можно пропустить этот цикл."""


class DiscordPresence:
    def __init__(self, client_id):
        self.client_id = client_id
        self.rpc = None

    def connect(self, retries=5, delay=3):
        """Подключается к локальному клиенту Discord, повторяя попытку,
        если Discord ещё не запущен или пайп не готов."""
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                self.rpc = Presence(client_id=self.client_id)
                self.rpc.connect()
                return
            except (DiscordNotFound, PipeClosed, Exception) as exc:
                last_exc = exc
                time.sleep(delay)
        raise ConnectionError(
            f"Не удалось подключиться к Discord после {retries} попыток: {last_exc}"
        )

    def update(self, **kwargs):
        if self.rpc is None:
            raise RuntimeError("Discord RPC не подключен, сначала вызови connect().")
        try:
            self.rpc.update(**kwargs)
            return
        except (PipeClosed, Exception) as first_exc:
            # Возможно, Discord закрылся/перезапустился — пробуем
            # переподключиться и повторить обновление. Ретраи здесь
            # короче, чем при первом запуске (connect() по умолчанию):
            # это может вызываться часто в фоновом цикле, и незачем
            # блокировать его на 15 секунд при каждой проверке.
            try:
                self.connect(retries=2, delay=1)
                self.rpc.update(**kwargs)
            except Exception as second_exc:
                raise PresenceUpdateError(
                    f"Discord отклонил обновление: {second_exc} "
                    f"(первая попытка: {first_exc})"
                ) from second_exc
