// background.js
//
// Background-скрипты выполняются в контексте самого расширения, а не
// посещаемой страницы — поэтому на них не действует Content-Security-
// -Policy сайта VK, который блокирует fetch к 127.0.0.1 из content
// script'ов. content.js передаёт сюда данные о треке через
// runtime.sendMessage и ждёт ответ: реальный fetch делает этот файл,
// а content.js запоминает трек как "отправленный" только после
// подтверждения — если локальный сервер (main.py/tray.py) ещё не
// запущен, попытка не проваливается молча навсегда, а будет повторена
// на следующем опросе (каждые 5 секунд), пока сервер не примет данные.

const ENDPOINT = "http://127.0.0.1:39285/track";

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
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
// страниц, соответствующих manifest.json. Если вкладка VK уже была
// открыта до того, как расширение установили/перезагрузили, скрипт
// сам туда не попадёт без обновления страницы (F5) — чтобы не
// заставлять делать это руками каждый раз, внедряем content.js во все
// уже открытые подходящие вкладки прямо сейчас, при старте фонового
// скрипта.
async function injectIntoExistingTabs() {
  try {
    const tabs = await browser.tabs.query({
      url: ["https://vk.ru/*", "https://vk.com/*"],
    });
    for (const tab of tabs) {
      try {
        await browser.tabs.executeScript(tab.id, { file: "content.js" });
      } catch (err) {
        // вкладка могла быть служебной/недоступной для инъекции — пропускаем
      }
    }
  } catch (err) {
    // browser.tabs недоступен или запрос не удался — не критично
  }
}

injectIntoExistingTabs();
