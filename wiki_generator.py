import requests
from typing import Dict
from pathlib import Path

class WikiDocumentationGenerator:
    """Генератор документации для MediaWiki"""
    
    def __init__(self, base_url: str, username: str, password: str, openai_client):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.openai_client = openai_client
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
        # Добавляем магические слова для отключения кнопок редактирования
        content = "__NOEDITSECTION__\n\n"
        content += f"= {project_name} =\n\n"
        
        # Добавляем оглавление
        content += "__TOC__\n\n"
        
        # Генерируем содержимое
        for directory in project_structure['directories']:
            if directory['type'] == 'directory':
                content += self._process_directory(directory)
            else:
                content += self._process_file(directory)

        # Сохраняем страницу
        self._save_page(project_name, content)
        
        # Формируем прямую ссылку на страницу
        page_url = f"{self.base_url}/index.php/{project_name}"
        return page_url

    def _process_directory(self, directory: Dict, level: int = 2) -> str:
        """Обработка директории"""
        content = f"{'=' * level} Директория: {directory['name']} {'=' * level}\n\n"
        content += f"Путь: <code>{directory['path']}</code>\n\n"
        
        for file in directory['files']:
            content += self._process_file(file, level + 1)
        
        return content

    def _process_file(self, file: Dict, level: int = 2) -> str:
        """Обработка файла"""
        content = f"{'=' * level} Файл: {file['name']} {'=' * level}\n\n"
        content += f"Путь: <code>{file['path']}</code>\n\n"

        # Обработка классов
        if file['classes']:
            for cls in file['classes']:
                content += self._process_class(cls, level + 1)

        # Обработка функций
        if file['functions']:
            content += f"{'=' * (level + 1)} Функции {'=' * (level + 1)}\n\n"
            for func in file['functions']:
                content += self._process_function(func)

        return content

    def _process_class(self, cls: Dict, level: int) -> str:
        """Обработка класса"""
        content = f"{'=' * level} Класс {cls['name']} {'=' * level}\n\n"
        
        # Генерация описания класса
        class_prompt = f"""Напиши подробное описание Python класса на основе следующей информации:
        Название: {cls['name']}
        Базовые классы: {', '.join(cls['bases'])}
        Docstring: {cls['docstring']}
        Методы: {[m['name'] for m in cls['methods']]}
        
        Опиши:
        1. Основное назначение класса
        2. Какие задачи решает
        3. Как взаимодействует с другими компонентами
        4. Особенности реализации
        
        Формат: простой текст, без заголовков, 3-4 предложения."""
        
        class_description = self._ask_gpt(class_prompt)
        content += f"{class_description}\n\n"
        
        if cls['bases']:
            content += f"Наследуется от: {', '.join(cls['bases'])}\n\n"
        
        if cls['docstring']:
            content += f"'''{cls['docstring']}'''\n\n"

        # Методы класса
        if cls['methods']:
            content += "==== Методы ====\n\n"
            for method in cls['methods']:
                content += self._process_function(method)

        return content

    def _process_function(self, func: Dict) -> str:
        """Обработка функции/метода"""
        content = f"===== {func['name']} =====\n\n"
        
        # Генерация описания функции
        func_prompt = f"""Напиши подробное описание Python функции/метода на основе:
        Название: {func['name']}
        Параметры: {[f"{arg['name']}: {arg['type']}" for arg in func['args']]}
        Возвращает: {func['returns']}
        Декораторы: {func['decorators']}
        Docstring: {func['docstring']}
        
        Опиши:
        1. Что делает функция
        2. Как использовать
        3. Особенности работы
        4. Примеры использования (если уместно)
        
        Формат: простой текст, без заголовков, 2-3 предложения."""
        
        func_description = self._ask_gpt(func_prompt)
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
        """Запрос к GPT для генерации описания"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT error: {e}")
            return "*Не удалось сгенерировать описание*"

    def _save_page(self, title: str, content: str):
        """Сохранение страницы в MediaWiki"""
        # Получаем токен для редактирования
        params = {
            'action': 'query',
            'meta': 'tokens',
            'format': 'json'
        }
        response = self.session.get(f"{self.base_url}/api.php", params=params)
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
        if 'error' in response.json():
            raise Exception(f"Failed to save page: {response.json()['error']}") 