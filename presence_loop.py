"""
presence_loop.py

Общая логика ожидания обновлений трека и применения их к Discord Rich
Presence. Вынесена отдельно, чтобы консольная версия (main.py) и
фоновая трей-версия (tray.py) не дублировали одну и ту же логику —
разница между ними только в том, как показывать результат (печать в
консоль или подсказка иконки в трее).

Браузерное расширение теперь шлёт данные каждые 5 секунд независимо от
того, менялся ли трек (это дёшево — чисто локальный запрос), поэтому
"пусто" от store.wait_for_update() почти никогда не приходит. Из-за
этого пересинхронизация с Discord (на случай, если сам Discord
перезапустили, пока трек не менялся) не может жить только в ветке
таймаута — она проверяется при каждом вызове, но реально отправляется
не чаще, чем раз в RESYNC_INTERVAL секунд.
"""

import time

from pypresence.types import ActivityType

from config import DEFAULT_LARGE_IMAGE_URL
from discord_presence import PresenceUpdateError
from logger import log

RESYNC_INTERVAL = 10  # секунд между повторными отправками одного и того же статуса


class PresenceLoop:
    def __init__(self, store, presence, config, lang):
        self.store = store
        self.presence = presence
        self.config = config
        self.lang = lang
        self.old_key = None
        self.warmed_covers = set()
        self.last_update_kwargs = None
        self.last_resync_at = 0.0
        self.last_data_at = None  # когда в последний раз реально пришли данные от VK
        self.discord_ok = True  # presence.connect() уже успешно отработал до создания цикла

    def wait_and_update(self, timeout=30):
        """Ждёт следующее обновление трека (или таймаут), применяет
        его к Discord Presence. Возвращает (track, messages):
        track — None, если новых данных не было или трек не
        изменился; messages — список строк-предупреждений на случай,
        если что-то пошло не так (Discord отклонил обложку и т.п.),
        чтобы вызывающий код сам решил, показывать их в консоли или
        только записать в лог."""
        track = self.store.wait_for_update(timeout=timeout)

        if track is not None:
            self.last_data_at = time.monotonic()

        if track is None:
            self._maybe_resync()
            return None, []

        key = f"{track.get('artist')}_{track.get('title')}"
        if key == self.old_key:
            # Тот же трек, что и был — просто пересинхронизация на
            # случай перезапуска Discord, не полноценное обновление.
            self._maybe_resync()
            return None, []
        self.old_key = key

        return self._apply_track(track)

    def _maybe_resync(self):
        """Досылает последний известный статус, если прошло достаточно
        времени с прошлой отправки — на случай, если Discord за это
        время перезапустили (например, обновление), пока трек на VK
        не менялся. Без этого статус мог бы пропасть до смены песни."""
        if self.last_update_kwargs is None:
            return
        now = time.monotonic()
        if now - self.last_resync_at < RESYNC_INTERVAL:
            return
        self.last_resync_at = now
        try:
            self.presence.update(**self.last_update_kwargs)
        except PresenceUpdateError:
            self.discord_ok = False
        else:
            self.discord_ok = True

    def _apply_track(self, track):
        messages = []

        cover_status = track.get("coverStatus", "missing")
        large_image = DEFAULT_LARGE_IMAGE_URL
        if cover_status == "missing":
            log(f'Нет обложки для "{track["title"]}" — {track["artist"]}: элемент обложки не найден на странице')
        elif cover_status == "too_long":
            log(
                f'Нет обложки для "{track["title"]}" — {track["artist"]}: '
                f'ссылка длиннее лимита Discord ({track.get("coverLength")} символов)'
            )
        elif track.get("cover"):
            large_image = track["cover"]

        update_kwargs = dict(
            activity_type=ActivityType.LISTENING,
            details=track["title"],
            state=track["artist"],
            large_image=large_image,
        )
        if track.get("trackUrl"):
            update_kwargs["details_url"] = track["trackUrl"]
        if self.config["small_image"]:
            update_kwargs["small_image"] = self.config["small_image"]
            update_kwargs["small_text"] = self.config["small_text"]

        try:
            self.presence.update(**update_kwargs)
        except PresenceUpdateError as exc:
            used_cover = large_image != DEFAULT_LARGE_IMAGE_URL
            if used_cover:
                messages.append(self._text("cover_rejected", exc))
                log(f'Discord отклонил обложку для "{track["title"]}" — {track["artist"]}: {exc}')
                update_kwargs["large_image"] = DEFAULT_LARGE_IMAGE_URL
                try:
                    self.presence.update(**update_kwargs)
                except PresenceUpdateError as exc2:
                    messages.append(self._text("update_rejected", exc2))
                    log(f'Discord отклонил обновление целиком для "{track["title"]}" — {track["artist"]}: {exc2}')
                    self.discord_ok = False
                else:
                    self._remember_success(update_kwargs)
            else:
                messages.append(self._text("update_rejected_no_cover", exc))
                log(f'Discord отклонил обновление (без обложки) для "{track["title"]}" — {track["artist"]}: {exc}')
                self.discord_ok = False
        else:
            self._remember_success(update_kwargs)
            # Discord иногда не успевает закешировать совсем новую
            # картинку к первому показу и рисует заглушку — если это
            # первый раз, когда мы используем именно эту обложку,
            # подождём немного и повторим то же обновление ещё раз.
            if large_image != DEFAULT_LARGE_IMAGE_URL and large_image not in self.warmed_covers:
                self.warmed_covers.add(large_image)
                time.sleep(3)
                try:
                    self.presence.update(**update_kwargs)
                except PresenceUpdateError:
                    pass  # не критично — первая отправка уже прошла успешно

        return track, messages

    def _remember_success(self, update_kwargs):
        self.last_update_kwargs = update_kwargs
        self.last_resync_at = time.monotonic()
        self.discord_ok = True

    def _text(self, kind, exc):
        texts = {
            "cover_rejected": {
                "ru": f"Discord отклонил обложку трека, пробую без неё: {exc}",
                "en": f"Discord rejected the cover image, retrying without it: {exc}",
            },
            "update_rejected": {
                "ru": f"Discord всё равно отклонил обновление, пропускаю этот трек: {exc}",
                "en": f"Discord still rejected the update, skipping this track: {exc}",
            },
            "update_rejected_no_cover": {
                "ru": f"Discord отклонил обновление статуса, пропускаю этот трек: {exc}",
                "en": f"Discord rejected the update, skipping this track: {exc}",
            },
        }
        return texts[kind]["ru" if self.lang == "ru" else "en"]
