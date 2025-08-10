import logging
import os
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


POLL_SECONDS: Final = 5
USER_AGENT: Final = "Mozilla/5.0 (compatible; AnapaBot/1.0)"

last_seen_id = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class Post:
    msg_id: int
    text: str
    url: str


def fetch_posts(channel_username: str) -> Sequence[Post]:
    url = f"https://t.me/s/{channel_username}"
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts: list[Post] = []
    for b in soup.select(".tgme_widget_message_wrap"):
        msg = b.select_one(".tgme_widget_message")
        if not msg:
            continue
        data_post = str(msg.get("data-post") or "")
        if "/" not in data_post:
            continue
        _, msg_id_str = data_post.split("/", 1)
        try:
            msg_id = int(re.findall(r"\d+", msg_id_str)[0])
        except Exception:  # noqa: BLE001
            continue
        text_el = b.select_one(".tgme_widget_message_text")
        text = text_el.get_text("\n", strip=True) if text_el else ""
        url = f"https://t.me/{channel_username}/{msg_id}"
        posts.append(Post(msg_id=msg_id, text=text, url=url))
    posts.sort(key=lambda x: x.msg_id)
    return posts


def send_message(text: str, bot_token: str, chat_id: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    r.raise_for_status()


@dataclass(kw_only=True, slots=True, frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: os.environ["APP_BOT_TOKEN"])
    channel_username: str = field(
        default_factory=lambda: os.environ["APP_CHANNEL_USERNAME"]
    )
    keyword: str = field(default_factory=lambda: os.environ["APP_KEYWORD"])
    chat_id: str = field(default_factory=lambda: os.environ["APP_CHAT_ID"])
    last_seen_id: int = field(
        default_factory=lambda: int(os.environ.get("APP_LAST_SEEN_ID", 0))
    )
    poll_seconds: int = field(
        default_factory=lambda: int(os.environ.get("APP_POLL_SECONDS", 5))
    )


def parse(config: Config) -> None:
    last_seen_id = config.last_seen_id
    logger.info(
        "Запущен мониторинг @%s на слово '%s'...",
        config.channel_username,
        config.keyword,
    )
    while True:
        try:
            posts = fetch_posts(channel_username=config.channel_username)
            new_posts = [p for p in posts if p.msg_id > last_seen_id]
            for post in new_posts:
                if config.keyword.casefold() in post.text.casefold():
                    snippet = (
                        (post.text[:500] + "…") if len(post.text) > 500 else post.text
                    )
                    send_message(
                        text=f"Найдено в @{config.channel_username} "
                        f"#{post.msg_id}:\n{post.url}\n\n{snippet}",
                        bot_token=config.bot_token,
                        chat_id=config.chat_id,
                    )
                    logger.info("→ Отправлено: %s", post.url)
            if new_posts:
                last_seen_id = max(last_seen_id, new_posts[-1].msg_id)
            time.sleep(config.poll_seconds)
        except KeyboardInterrupt:
            logger.info("Остановлено пользователем.")
            break
        except Exception as e:  # noqa: BLE001
            logger.info("Ошибка: %s", e)
            time.sleep(config.poll_seconds)
