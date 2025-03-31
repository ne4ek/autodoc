import logging
from pathlib import Path

def setup_logger():
    """Настройка логгера"""
    # Создаем директорию для логов если её нет
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Настраиваем формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настраиваем вывод в файл
    file_handler = logging.FileHandler(log_dir / 'documentation_generator.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Настраиваем вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger 