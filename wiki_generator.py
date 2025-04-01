import requests
from typing import Dict
from pathlib import Path
import logging
from urllib.parse import quote
from llm_providers import LLMProvider
import time

logger = logging.getLogger(__name__)

class WikiDocumentationGenerator:
    """Генератор документации для MediaWiki"""
    
    def __init__(self, base_url: str, username: str, password: str, llm_provider: LLMProvider):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.llm_provider = llm_provider  # Переименовано из openai_client
        logger.info("Инициализация генератора Wiki документации")
        self._login(username, password)

    def _login(self, username: str, password: str):
        """Авторизация в MediaWiki"""
        # Получаем токен для входа
        params = {
            'action': 'query',
            'meta': 'tokens',
            'type': 'login',
            'format': 'json'
        }
        response = self.session.get(f"{self.base_url}/api.php", params=params)
        login_token = response.json()['query']['tokens']['logintoken']

        # Выполняем вход
        data = {
            'action': 'login',
            'lgname': username,
            'lgpassword': password,
            'lgtoken': login_token,
            'format': 'json'
        }
        response = self.session.post(f"{self.base_url}/api.php", data=data)
        if response.json()['login']['result'] != 'Success':
            raise Exception("Failed to login to MediaWiki")

    def generate_docs(self, project_structure: Dict) -> str:
        """Генерация документации в формате MediaWiki
        
        Returns:
            str: URL страницы с документацией
        """
        project_name = project_structure['name']
        logger.info(f"Начало генерации документации для проекта: {project_name}")
        
        # Добавляем магические слова для отключения кнопок редактирования
        content = "__NOEDITSECTION__\n\n"
        content += f"= {project_name} =\n\n"
        
        # Добавляем оглавление
        content += "__TOC__\n\n"
        
        # Генерируем содержимое
        for directory in project_structure['directories']:
            if directory['type'] == 'directory':
                logger.info(f"Обработка директории: {directory['name']}")
                content += self._process_directory(directory)
            else:
                logger.info(f"Обработка файла: {directory['name']}")
                content += self._process_file(directory)

        # Сохраняем страницу и получаем корректный URL
        self._save_page(project_name, content)
        
        # Формируем корректную ссылку на страницу
        page_url = f"{self.base_url}/index.php/{quote(project_name)}"
        logger.info(f"Документация сохранена: {page_url}")
        return page_url

    def _process_directory(self, directory: Dict, level: int = 2) -> str:
        """Обработка директории"""
        logger.info(f"Генерация документации для директории: {directory['name']}")
        content = f"{'=' * level} Директория: {directory['name']} {'=' * level}\n\n"
        content += f"Путь: <code>{directory['path']}</code>\n\n"
        
        for file in directory['files']:
            content += self._process_file(file, level + 1)
        
        return content

    def _process_file(self, file: Dict, level: int = 2) -> str:
        """Обработка файла"""
        logger.info(f"Генерация документации для файла: {file['name']}")
        content = f"{'=' * level} Файл: {file['name']} {'=' * level}\n\n"
        content += f"Путь: #{file['path']}\n\n"

        # Обработка классов
        if file['classes']:
            for cls in file['classes']:
                # Устанавливаем родительский путь
                cls['parent_path'] = file['path']
                content += self._process_class(cls, level + 1)

        # Обработка функций
        if file['functions']:
            content += f"{'=' * (level + 1)} Функции {'=' * (level + 1)}\n\n"
            for func in file['functions']:
                # Устанавливаем родительский путь
                func['parent_path'] = file['path']
                content += self._process_function(func)

        return content

    def _process_class(self, cls: Dict, level: int) -> str:
        """Обработка класса"""
        logger.info(f"Обработка класса: {cls['name']}")
        content = f"{'=' * level} Класс {cls['name']} {'=' * level}\n\n"
        
        # Добавляем путь с номером строки
        parent_path = cls.get('parent_path', '')
        path_with_line = f"{parent_path}:{cls['line_number']}" if parent_path else ''
        if path_with_line:
            content += f"Путь: #{path_with_line}\n\n"
        
        # Обновленный промпт с акцентом на словесное описание
        class_prompt = f"""Проанализируй этот Python класс и предоставь ТОЛЬКО словесное описание:
        Название: {cls['name']}
        Базовые классы: {', '.join(cls['bases'])}
        Методы: {[m['name'] for m in cls['methods']]}
        Docstring: {cls['docstring']}
        
        Код класса (только для анализа):
        ```python
        {cls['source_code'][:500]}
        ```
        
        ВАЖНО: В ответе НЕ ВКЛЮЧАЙ исходный код, примеры кода или синтаксис.
        Дай ТОЛЬКО чисто словесное описание того, что делает класс, его назначение и как он используется.
        Опиши человеческим языком, как будто объясняешь коллеге, не используя технические термины там, где это не обязательно.
        Ответ должен быть 3-4 четкими и понятными предложениями.
        """
        
        logger.info(f"Запрос описания для класса: {cls['name']}")
        class_description = self._ask_gpt(class_prompt)
        logger.info(f"Получено описание длиной {len(class_description)} символов")
        
        content += f"{class_description}\n\n"
        
        if cls['bases']:
            content += f"Наследуется от: {', '.join(cls['bases'])}\n\n"
        
        if cls['docstring']:
            content += f"'''{cls['docstring']}'''\n\n"

        # Методы класса
        if cls['methods']:
            content += "==== Методы ====\n\n"
            logger.info(f"Обработка {len(cls['methods'])} методов класса {cls['name']}")
            for i, method in enumerate(cls['methods']):
                logger.info(f"Обработка метода {i+1}/{len(cls['methods'])}: {method['name']}")
                method['parent_path'] = cls.get('parent_path', '')
                content += self._process_function(method)

        return content

    def _process_function(self, func: Dict) -> str:
        """Обработка функции/метода"""
        logger.info(f"Обработка функции/метода: {func['name']}")
        content = f"===== {func['name']} =====\n\n"
        
        # Добавляем путь с номером строки
        parent_path = func.get('parent_path', '')
        path_with_line = f"{parent_path}:{func['line_number']}" if parent_path else ''
        if path_with_line:
            content += f"Путь: #{path_with_line}\n\n"
        
        # Обновленный промпт с акцентом на словесное описание
        func_prompt = f"""Проанализируй эту Python функцию и предоставь ТОЛЬКО словесное описание:
        Название: {func['name']}
        Параметры: {[f"{arg['name']}: {arg['type']}" for arg in func['args']]}
        Возвращает: {func['returns']}
        Docstring: {func['docstring']}
        
        Код функции (только для анализа):
        ```python
        {func['source_code'][:500]}
        ```
        
        ВАЖНО: В ответе НЕ ВКЛЮЧАЙ исходный код, примеры кода или синтаксис. 
        Дай ТОЛЬКО чисто словесное описание того, что делает функция, как она работает и для чего используется.
        Опиши человеческим языком, как будто объясняешь коллеге, не используя технические термины там, где это не обязательно.
        Ответ должен быть 2-3 четкими и понятными предложениями.
        """
        
        logger.info(f"Запрос описания для функции: {func['name']}")
        func_description = self._ask_gpt(func_prompt)
        logger.info(f"Получено описание длиной {len(func_description)} символов")
        
        content += f"{func_description}\n\n"
        
        # Сигнатура функции
        signature = f"{func['name']}("
        args = []
        for arg in func['args']:
            arg_str = arg['name']
            if arg['type']:
                arg_str += f": {arg['type']}"
            args.append(arg_str)
        signature += ", ".join(args) + ")"
        if func['returns']:
            signature += f" -> {func['returns']}"
        
        content += f"<code>{signature}</code>\n\n"

        if func['docstring']:
            content += f"'''{func['docstring']}'''\n\n"

        if func['decorators']:
            content += "Декораторы:\n"
            for decorator in func['decorators']:
                content += f"* <code>@{decorator}</code>\n"
            content += "\n"

        return content

    def _ask_gpt(self, prompt: str, max_tokens: int = 1000) -> str:
        """Запрос к языковой модели"""
        method_name = "неизвестный метод"
        # Попытка извлечь имя метода из промпта
        for line in prompt.split("\n"):
            if "Название:" in line:
                method_name = line.split("Название:")[1].strip()
                break
                
        logger.info(f"Отправка запроса к ИИ для: {method_name}")
        
        try:
            start_time = time.time()
            response = self.llm_provider.generate_text(prompt, max_tokens)
            elapsed_time = time.time() - start_time
            
            logger.info(f"Запрос выполнен за {elapsed_time:.2f} секунд")
            logger.info(f"Полученный ответ ({len(response)} символов): {response[:50]}...")
            
            return response
        except Exception as e:
            logger.error(f"Ошибка при запросе к ИИ: {e}", exc_info=True)
            return "*Не удалось сгенерировать описание*"

    def _save_page(self, title: str, content: str):
        """Сохранение страницы в MediaWiki"""
        try:
            # Получаем токен для редактирования
            params = {
                'action': 'query',
                'meta': 'tokens',
                'format': 'json'
            }
            response = self.session.get(f"{self.base_url}/api.php", params=params)
            response.raise_for_status()  # Проверяем на ошибки HTTP
            edit_token = response.json()['query']['tokens']['csrftoken']

            # Сохраняем страницу
            data = {
                'action': 'edit',
                'title': title,
                'text': content,
                'token': edit_token,
                'format': 'json'
            }
            response = self.session.post(f"{self.base_url}/api.php", data=data)
            response.raise_for_status()  # Проверяем на ошибки HTTP
            
            result = response.json()
            if 'error' in result:
                raise Exception(f"Failed to save page: {result['error']}")
            
            logger.info(f"Страница '{title}' успешно сохранена в MediaWiki")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении страницы в MediaWiki: {e}", exc_info=True)
            raise 