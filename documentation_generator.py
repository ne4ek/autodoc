import json
from pathlib import Path
from typing import Dict
import openai
import markdown2

class DocumentationGenerator:
    """Генератор документации с GPT-4"""
    def __init__(self, openai_key: str):
        self.client = openai.OpenAI(api_key=openai_key)
    
    def generate_docs(self, project_structure: Dict, output_path: str = "docs"):
        """Генерация всей документации"""
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True)
        
        self._generate_project_overview(project_structure, output_dir)
        
        for directory in project_structure['directories']:
            if directory['type'] == 'directory':
                self._process_directory(directory, output_dir)
            else:
                self._process_file(directory, output_dir)

    def _generate_project_overview(self, project: Dict, output_dir: Path):
        """Генерация главной страницы проекта"""
        content = f"# {project['name']}\n\n"
        content += "## Структура проекта\n\n"
        
        content += "```\n"
        for directory in project['directories']:
            content += self._generate_dir_tree(directory, prefix="")
        content += "```\n\n"
        
        prompt = f"Напиши краткое описание Python проекта {project['name']} на основе его структуры:\n{json.dumps(project, indent=2)}"
        description = self._ask_gpt(prompt, max_tokens=500)
        content += f"## Описание проекта\n\n{description}\n"
        
        self._save_markdown(output_dir / "OVERVIEW.md", content)

    def _generate_dir_tree(self, node: Dict, prefix: str = "") -> str:
        """Генерация ASCII-дерева структуры"""
        tree = f"{prefix}├── {node['name']}\n"
        
        if node['type'] == 'directory':
            for i, file in enumerate(node['files']):
                is_last = i == len(node['files']) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                tree += self._generate_dir_tree(file, new_prefix)
        elif node['type'] == 'file':
            if node['classes']:
                tree += f"{prefix}│   ├── [Classes]\n"
                for cls in node['classes']:
                    tree += f"{prefix}│   │   ├── {cls['name']}\n"
            if node['functions']:
                tree += f"{prefix}│   ├── [Functions]\n"
                for func in node['functions']:
                    tree += f"{prefix}│   │   ├── {func['name']}\n"
        
        return tree

    def _process_directory(self, directory: Dict, parent_dir: Path):
        """Обработка директории"""
        dir_path = parent_dir / directory['name']
        dir_path.mkdir(exist_ok=True)
        
        content = f"# Директория: {directory['name']}\n\n"
        content += f"Путь: `{directory['path']}`\n\n"
        
        prompt = f"Напиши краткое описание директории {directory['name']} Python проекта на основе её содержимого:\n{json.dumps(directory, indent=2)}"
        description = self._ask_gpt(prompt, max_tokens=300)
        content += f"## Описание\n\n{description}\n\n"
        
        content += "## Файлы\n"
        for file in directory['files']:
            content += f"- [{file['name']}]({file['name']}.md)\n"
        
        self._save_markdown(dir_path / "README.md", content)
        
        for file in directory['files']:
            self._process_file(file, dir_path)

    def _process_file(self, file: Dict, parent_dir: Path):
        """Обработка файла"""
        content = f"# Файл: {file['name']}\n\n"
        content += f"Путь: `{file['path']}`\n\n"
        
        prompt = f"Напиши краткое описание Python файла {file['name']} на основе его содержимого:\n{json.dumps(file, indent=2)}"
        description = self._ask_gpt(prompt, max_tokens=400)
        content += f"## Описание файла\n\n{description}\n\n"
        
        if file['classes']:
            content += "## Классы\n"
            for cls in file['classes']:
                content += self._generate_class_docs(cls)
        
        if file['functions']:
            content += "## Функции\n"
            for func in file['functions']:
                content += self._generate_function_docs(func)
        
        self._save_markdown(parent_dir / f"{file['name']}.md", content)

    def _generate_class_docs(self, cls: Dict) -> str:
        """Генерация документации класса"""
        prompt = f"""Сгенерируй Markdown документацию для Python класса на основе следующей информации:
        Название: {cls['name']}
        Базовые классы: {', '.join(cls['bases'])}
        Docstring: {cls['docstring']}
        Методы: {[m['name'] for m in cls['methods']]}
        
        Включи:
        1. Назначение класса
        2. Описание каждого метода
        3. Пример использования
        4. Mermaid-диаграмму класса
        """
        return f"\n### Класс `{cls['name']}`\n\n{self._ask_gpt(prompt)}\n"

    def _generate_function_docs(self, func: Dict) -> str:
        """Генерация документации функции"""
        params = "\n".join([f"- {arg['name']}: {arg['type'] or 'тип не указан'}" for arg in func['args']])
        decorators = "\n".join([f"- `{d}`" for d in func['decorators']]) if func['decorators'] else "нет"
        
        prompt = f"""Сгенерируй Markdown документацию для Python функции на основе:
        Название: {func['name']}
        Параметры:
        {params}
        Возвращает: {func['returns'] or 'тип не указан'}
        Декораторы: {decorators}
        Docstring: {func['docstring']}
        
        Включи:
        1. Назначение функции
        2. Подробное описание параметров
        3. Возвращаемое значение
        4. Пример вызова
        5. Особенности (если есть декораторы)
        """
        return f"\n### Функция `{func['name']}`\n\n{self._ask_gpt(prompt)}\n"

    def _ask_gpt(self, prompt: str, max_tokens: int = 1000) -> str:
        """Запрос к GPT-4"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT error: {e}")
            return f"*Не удалось сгенерировать описание: {str(e)}*"

    def _save_markdown(self, path: Path, content: str):
        """Сохранение Markdown файла"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Документация сохранена: {path}") 