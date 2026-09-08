// content.js
//
// Работает в контексте открытой вкладки vk.ru/vk.com. Читает текущий
// трек прямо из верхнего плеера страницы (общий для всех разделов VK)
// и передаёт его background.js через runtime.sendMessage — сам fetch
// выполняется уже в background.js, в контексте расширения, чтобы не
// упираться в Content-Security-Policy самой страницы VK (она
// запрещает fetch со страницы на 127.0.0.1).
//
// Отправляем данные каждый опрос (раз в 5 сек), даже если трек не
// изменился — это чисто локальный запрос на 127.0.0.1, ничего внешнего
// не задействовано, так что "спамить" тут нечего. Зато это делает
// систему устойчивой к перезапуску Python-скрипта или самого Discord:
// не нужно ждать смены трека, чтобы всё пересинхронизировалось —
// достаточно подождать максимум 5 секунд. Дедупликация перед реальной
// отправкой в Discord всё равно происходит на стороне Python.

(function () {
  "use strict";

  const POLL_INTERVAL_MS = 5000;

  const TITLE_SELECTOR = '[data-testid="AudioPlayerBlock_AudioTitle"]';
  const ARTIST_SELECTOR = '[data-testid="AudioPlayerBlock_Authors"]';
  const COVER_SELECTOR = '[data-testid="AudioPlayerBlock_AudioCover"] img';

  // Discord отклоняет large_image длиннее 300 символов. VK иногда
  // кладёт в один URL сразу несколько вариантов размера через запятую
  // (например "_280x1280,1440x1440,1500x1500"), из-за чего ссылка
  // вылезает за лимит — обрезаем до одного варианта размера вместо
  // того чтобы совсем отказываться от обложки.
  const MAX_IMAGE_URL_LENGTH = 300;
  const MULTI_SIZE_RE = /(_\d+x\d+)(?:,\d+x\d+)+/;

  let pendingKey = null; // не даём двум запросам на один и тот же трек лететь одновременно

  function shortenCoverUrl(url) {
    if (url.length <= MAX_IMAGE_URL_LENGTH) return url;
    return url.replace(MULTI_SIZE_RE, "$1");
  }

  function extractTrack() {
    const titleEl = document.querySelector(TITLE_SELECTOR);
    const artistEl = document.querySelector(ARTIST_SELECTOR);
    if (!titleEl || !artistEl) return null;

    const title = titleEl.textContent.trim();
    const artist = artistEl.textContent.trim();
    if (!title || !artist) return null;

    // TITLE_SELECTOR указывает прямо на <a href="...">, так что
    // .href уже возвращает готовую абсолютную ссылку на трек.
    const trackUrl = titleEl.href || null;

    const coverEl = document.querySelector(COVER_SELECTOR);
    let cover = null;
    let coverStatus = "missing";
    let coverLength = 0;

    if (coverEl && coverEl.src) {
      const shortened = shortenCoverUrl(coverEl.src);
      coverLength = shortened.length;
      if (coverLength > MAX_IMAGE_URL_LENGTH) {
        coverStatus = "too_long";
      } else {
        cover = shortened;
        coverStatus = "ok";
      }
    }

    return { title, artist, cover, coverStatus, coverLength, trackUrl };
  }

  function send(track) {
    const key = track.artist + "_" + track.title;
    if (key === pendingKey) return; // на этот же трек уже есть незавершённая попытка

    pendingKey = key;
    browser.runtime
      .sendMessage({ type: "vkrpc-track", track })
      .catch(() => {
        // локальный сервер сейчас не запущен — не страшно, повторим
        // на следующем опросе через 5 секунд
      })
      .finally(() => {
        if (pendingKey === key) pendingKey = null;
      });
  }

  setInterval(() => {
    const track = extractTrack();
    if (track) send(track);
  }, POLL_INTERVAL_MS);
})();
