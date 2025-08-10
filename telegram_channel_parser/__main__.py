import logging

from telegram_channel_parser.parser import Config, parse


logging.basicConfig(
    level=logging.INFO,  # Минимальный уровень сообщений
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    config = Config()
    parse(config=config)


if __name__ == "__main__":
    main()
