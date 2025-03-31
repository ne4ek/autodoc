import os
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения из .env файла
load_dotenv()

# Проверяем наличие обязательных переменных окружения
required_vars = [
    'PROJECT_PATH',
    'OUTPUT_DIR',
    'OPENAI_API_KEY',
    'MEDIAWIKI_BASE_URL',
    'MEDIAWIKI_USERNAME',
    'MEDIAWIKI_PASSWORD',
    'DOCUMENTATION_OUTPUT'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Конфигурационные параметры
PROJECT_PATH = Path(os.getenv('PROJECT_PATH'))
OUTPUT_DIR = os.getenv('OUTPUT_DIR')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

# MediaWiki конфигурация
MEDIAWIKI_BASE_URL = os.getenv('MEDIAWIKI_BASE_URL')
MEDIAWIKI_USERNAME = os.getenv('MEDIAWIKI_USERNAME')
MEDIAWIKI_PASSWORD = os.getenv('MEDIAWIKI_PASSWORD')

# Способ сохранения документации
DOCUMENTATION_OUTPUT = int(os.getenv('DOCUMENTATION_OUTPUT'))

# Проверка валидности DOCUMENTATION_OUTPUT
if DOCUMENTATION_OUTPUT not in (1, 2, 3):
    raise ValueError("DOCUMENTATION_OUTPUT must be 1, 2, or 3") 