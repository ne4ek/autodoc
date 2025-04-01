import json
import logging
import time
from project_analyzer import ProjectAnalyzer
from sonar_analyzer import SonarQubeAnalyzer
from documentation_generator import DocumentationGenerator
from wiki_generator import WikiDocumentationGenerator
from logger_config import setup_logger
from config import (
    PROJECT_PATH, OPENAI_KEY, OUTPUT_DIR,
    MEDIAWIKI_BASE_URL, MEDIAWIKI_USERNAME, MEDIAWIKI_PASSWORD,
    DOCUMENTATION_OUTPUT, LLM_PROVIDER, 
    WIZARDCODER_MODEL, WIZARDCODER_HOST,
    ANALYZER_TYPE, SONARQUBE_URL, SONARQUBE_TOKEN
)
from llm_providers import OpenAIProvider, OllamaProvider

logger = logging.getLogger(__name__)

def get_llm_provider():
    """Получение провайдера LLM на основе конфигурации"""
    if LLM_PROVIDER.lower() == 'openai':
        return OpenAIProvider(OPENAI_KEY)
    elif LLM_PROVIDER.lower() == 'wizardcoder':
        return OllamaProvider(WIZARDCODER_MODEL, WIZARDCODER_HOST)
    else:
        raise ValueError(f"Неизвестный провайдер LLM: {LLM_PROVIDER}")

def get_analyzer():
    """Получение анализатора проекта на основе конфигурации"""
    if ANALYZER_TYPE.lower() == 'ast':
        return ProjectAnalyzer(PROJECT_PATH)
    elif ANALYZER_TYPE.lower() == 'sonarqube':
        if not SONARQUBE_TOKEN:
            raise ValueError("Не указан токен SonarQube. Добавьте SONARQUBE_TOKEN в .env")
        return SonarQubeAnalyzer(PROJECT_PATH, SONARQUBE_URL, SONARQUBE_TOKEN)
    else:
        raise ValueError(f"Неизвестный тип анализатора: {ANALYZER_TYPE}")

def main():
    # Настройка логирования
    setup_logger()
    logger.info("Запуск генератора документации")
    
    try:
        # Инициализация LLM провайдера
        llm_provider = get_llm_provider()
        logger.info(f"Используется провайдер: {type(llm_provider).__name__}")
        
        # Получение анализатора
        analyzer = get_analyzer()
        logger.info(f"Используется анализатор: {type(analyzer).__name__}")
        
        # Анализ структуры проекта
        logger.info("Начало анализа структуры проекта")
        project_structure = analyzer.analyze()
        
        # Сохранение сырых данных (для отладки)
        with open('project_structure.json', 'w', encoding='utf-8') as f:
            json.dump(project_structure, f, indent=2, ensure_ascii=False)
        logger.info("Структура проекта сохранена в project_structure.json")
        
        # Генерация документации
        if DOCUMENTATION_OUTPUT in (1, 3):
            logger.info("Генерация локальной документации")
            doc_gen = DocumentationGenerator(OPENAI_KEY)  # TODO: Обновить для использования llm_provider
            doc_gen.generate_docs(project_structure, OUTPUT_DIR)
            logger.info(f"Локальная документация сгенерирована в папке {OUTPUT_DIR}")

        if DOCUMENTATION_OUTPUT in (2, 3):
            logger.info("Генерация документации в MediaWiki")
            wiki_gen = WikiDocumentationGenerator(
                MEDIAWIKI_BASE_URL,
                MEDIAWIKI_USERNAME,
                MEDIAWIKI_PASSWORD,
                llm_provider
            )
            wiki_url = wiki_gen.generate_docs(project_structure)
            logger.info(f"Документация сохранена в MediaWiki: {wiki_url}")
        
        logger.info("Генерация документации успешно завершена")
        
    except Exception as e:
        logger.error("Произошла ошибка при генерации документации", exc_info=True)
        raise

if __name__ == "__main__":
    main()