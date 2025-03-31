import json
import openai
from project_analyzer import ProjectAnalyzer
from documentation_generator import DocumentationGenerator
from wiki_generator import WikiDocumentationGenerator
from logger_config import setup_logger
from config import (
    PROJECT_PATH, OPENAI_KEY, OUTPUT_DIR,
    MEDIAWIKI_BASE_URL, MEDIAWIKI_USERNAME, MEDIAWIKI_PASSWORD,
    DOCUMENTATION_OUTPUT, LLM_PROVIDER, 
    WIZARDCODER_MODEL, WIZARDCODER_HOST
)
import logging
from llm_providers import OpenAIProvider, OllamaProvider

logger = logging.getLogger(__name__)

def get_llm_provider():
    """Получение провайдера LLM на основе конфигурации"""
    if LLM_PROVIDER.lower() == 'openai':
        return OpenAIProvider(OPENAI_KEY)
    elif LLM_PROVIDER.lower() == 'wizardcoder':
        return OllamaProvider(WIZARDCODER_HOST)
    else:
        raise ValueError(f"Неизвестный провайдер LLM: {LLM_PROVIDER}")

def main():
    # Настройка логирования
    setup_logger()
    logger.info("Запуск генератора документации")
    
    # Инициализация OpenAI клиента
    openai_client = get_llm_provider()
    
    try:
        # 1. Анализ структуры проекта
        logger.info("Начало анализа структуры проекта")
        analyzer = ProjectAnalyzer(PROJECT_PATH)
        project_structure = analyzer.analyze()
        
        # Сохранение сырых данных (для отладки)
        with open('project_structure.json', 'w', encoding='utf-8') as f:
            json.dump(project_structure, f, indent=2, ensure_ascii=False)
        logger.info("Структура проекта сохранена в project_structure.json")
        
        # 2. Генерация документации
        if DOCUMENTATION_OUTPUT in (1, 3):
            logger.info("Генерация локальной документации")
            doc_gen = DocumentationGenerator(OPENAI_KEY)
            doc_gen.generate_docs(project_structure, OUTPUT_DIR)
            logger.info(f"Локальная документация сгенерирована в папке {OUTPUT_DIR}")

        if DOCUMENTATION_OUTPUT in (2, 3):
            logger.info("Генерация документации в MediaWiki")
            wiki_gen = WikiDocumentationGenerator(
                MEDIAWIKI_BASE_URL,
                MEDIAWIKI_USERNAME,
                MEDIAWIKI_PASSWORD,
                openai_client
            )
            wiki_url = wiki_gen.generate_docs(project_structure)
            logger.info(f"Документация сохранена в MediaWiki: {wiki_url}")
        
        logger.info("Генерация документации успешно завершена")
        
    except Exception as e:
        logger.error("Произошла ошибка при генерации документации", exc_info=True)
        raise

if __name__ == "__main__":
    main()