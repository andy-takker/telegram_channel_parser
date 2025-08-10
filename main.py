import os
import re
import time
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("APP_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("APP_CHANNEL_USERNAME")  # без @
CHAT_ID = os.getenv("APP_CHAT_ID")  # строка, для группы начинается с -100
KEYWORD = "анапа"
POLL_SECONDS = 5
USER_AGENT = "Mozilla/5.0 (compatible; AnapaBot/1.0)"

if not BOT_TOKEN or not CHANNEL_USERNAME or not CHAT_ID:
    raise SystemExit("Ошибка: нужно задать BOT_TOKEN, CHANNEL_USERNAME и CHAT_ID как переменные окружения.")

last_seen_id = 0

def fetch_posts():
    url = f"https://t.me/s/{CHANNEL_USERNAME}"
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for b in soup.select(".tgme_widget_message_wrap"):
        msg = b.select_one(".tgme_widget_message")
        if not msg:
            continue
        data_post = msg.get("data-post") or ""
        if "/" not in data_post:
            continue
        _, msg_id_str = data_post.split("/", 1)
        try:
            msg_id = int(re.findall(r"\d+", msg_id_str)[0])
        except:
            continue
        text_el = b.select_one(".tgme_widget_message_text")
        text = text_el.get_text("\n", strip=True) if text_el else ""
        url = f"https://t.me/{CHANNEL_USERNAME}/{msg_id}"
        posts.append((msg_id, text, url))
    posts.sort(key=lambda x: x[0])
    return posts

def send_message(text):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20
    )
    r.raise_for_status()

print(f"Запущен мониторинг @{CHANNEL_USERNAME} на слово '{KEYWORD}'...")
while True:
    try:
        posts = fetch_posts()
        new_posts = [p for p in posts if p[0] > last_seen_id]
        for msg_id, text, url in new_posts:
            if KEYWORD.casefold() in text.casefold():
                snippet = (text[:500] + "…") if len(text) > 500 else text
                send_message(f"Найдено в @{CHANNEL_USERNAME} #{msg_id}:\n{url}\n\n{snippet}")
                print(f"→ Отправлено: {url}")
        if new_posts:
            last_seen_id = max(last_seen_id, max(p[0] for p in new_posts))
        time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("Остановлено пользователем.")
        break
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(POLL_SECONDS)
