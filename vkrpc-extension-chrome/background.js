// background.js (Chrome/Chromium, Manifest V3)
//
// Service worker выполняется в привилегированном контексте расширения
// — на него не действует Content-Security-Policy страницы VK, которая
// блокирует fetch к 127.0.0.1 из content script'ов. content.js
// передаёт сюда данные о треке через runtime.sendMessage и ждёт ответ:
// content.js помечает трек как отправленный только при подтверждении.
//
// Service worker в MV3 не персистентный (может "засыпать" в простое),
// но автоматически просыпается на входящее сообщение — для наших
// сообщений раз в 5 секунд это не проблема.

const ENDPOINT = "http://127.0.0.1:39285/track";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "vkrpc-track") return;

  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message.track),
  })
    .then(() => sendResponse({ ok: true }))
    .catch(() => sendResponse({ ok: false }));

  return true; // держим канал ответа открытым для асинхронного fetch
});

// Content-script автоматически внедряется только в НОВЫЕ загрузки
// страниц. Если вкладка VK уже была открыта до установки/перезагрузки
// расширения, скрипт сам туда не попадёт без обновления страницы (F5)
// — чтобы не заставлять делать это руками, внедряем content.js во все
// уже открытые подходящие вкладки прямо сейчас, при старте service
// worker'а. В MV3 для этого используется chrome.scripting вместо
// устаревшего tabs.executeScript.
async function injectIntoExistingTabs() {
  try {
    const tabs = await chrome.tabs.query({
      url: ["https://vk.ru/*", "https://vk.com/*"],
    });
    for (const tab of tabs) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ["content.js"],
        });
      } catch (err) {
        // вкладка могла быть недоступна для инъекции — пропускаем
      }
    }
  } catch (err) {
    // запрос списка вкладок не удался — не критично
  }
}

injectIntoExistingTabs();
