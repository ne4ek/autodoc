import json
import openai
from project_analyzer import ProjectAnalyzer
from documentation_generator import DocumentationGenerator
from wiki_generator import WikiDocumentationGenerator
from config import (
    PROJECT_PATH, OPENAI_KEY, OUTPUT_DIR,
    MEDIAWIKI_BASE_URL, MEDIAWIKI_USERNAME, MEDIAWIKI_PASSWORD,
    DOCUMENTATION_OUTPUT
)

def main():
    # Инициализация OpenAI клиента
    openai_client = openai.OpenAI(api_key=OPENAI_KEY)
    
    # 1. Анализ структуры проекта
    print("Анализ структуры проекта...")
    analyzer = ProjectAnalyzer(PROJECT_PATH)
    project_structure = analyzer.analyze()
    
    # Сохранение сырых данных (для отладки)
    with open('project_structure.json', 'w', encoding='utf-8') as f:
        json.dump(project_structure, f, indent=2, ensure_ascii=False)
    
    # 2. Генерация документации
    if DOCUMENTATION_OUTPUT in (1, 3):
        print("Генерация локальной документации...")
        doc_gen = DocumentationGenerator(OPENAI_KEY)
        doc_gen.generate_docs(project_structure, OUTPUT_DIR)
        print(f"Локальная документация сгенерирована в папке {OUTPUT_DIR}")

    if DOCUMENTATION_OUTPUT in (2, 3):
        print("Генерация документации в MediaWiki...")
        wiki_gen = WikiDocumentationGenerator(
            MEDIAWIKI_BASE_URL,
            MEDIAWIKI_USERNAME,
            MEDIAWIKI_PASSWORD,
            openai_client
        )
        wiki_url = wiki_gen.generate_docs(project_structure)
        print(f"Документация сохранена в MediaWiki: {wiki_url}")

if __name__ == "__main__":
    main()