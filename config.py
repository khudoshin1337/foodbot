import os
import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# Настройка форматирования
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Файловый handler с ротацией
file_handler = RotatingFileHandler(
    'bot.log',
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# Консольный handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Настройка корневого логгера
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Загрузка переменных из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
FOOD_API_KEY = "iYNcjx3WdiVo8iHPixsQjsTyVNWvBeuyB0EDeYW3"

if not BOT_TOKEN or not WEATHER_API_KEY:
    raise ValueError("Не установлены необходимые переменные окружения") 