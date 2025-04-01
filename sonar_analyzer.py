import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from sonarqube import SonarQubeClient

logger = logging.getLogger(__name__)

class SonarQubeAnalyzer:
    """Анализатор проекта с использованием SonarQube"""
    
    def __init__(self, project_path: str, sonar_url: str, sonar_token: str):
        """
        Инициализация анализатора SonarQube
        
        Args:
            project_path: Путь к анализируемому проекту
            sonar_url: URL сервера SonarQube (например, http://localhost:9000)
            sonar_token: Токен доступа к SonarQube API
        """
        self.project_path = Path(project_path)
        self.project_key = self.project_path.name.lower().replace(' ', '_')
        self.sonar = SonarQubeClient(sonarqube_url=sonar_url, token=sonar_token)
        logger.info(f"Инициализация SonarQube анализатора для проекта: {self.project_path}")
    
    def analyze(self) -> Dict:
        """Анализ проекта с использованием SonarQube"""
        logger.info("Начало анализа структуры проекта с SonarQube")
        
        # Проверяем, существует ли проект в SonarQube
        self._ensure_project_exists()
        
        # Запускаем анализ проекта через SonarQube Scanner
        self._run_scanner()
        
        # Ждем завершения анализа
        self._wait_for_analysis_completion()
        
        # Получаем результаты анализа
        project_data = self._get_project_data()
        
        logger.info("Анализ структуры проекта с SonarQube завершен")
        return project_data
    
    def _ensure_project_exists(self):
        """Проверка наличия проекта в SonarQube, создание если не существует"""
        try:
            # Проверяем, существует ли проект
            projects = list(self.sonar.projects.search_projects(projects=self.project_key))
            
            if not projects:
                logger.info(f"Создание проекта в SonarQube: {self.project_key}")
                # Создаем проект
                self.sonar.projects.create_project(
                    project=self.project_key,
                    name=self.project_path.name,
                    visibility="private"
                )
        except Exception as e:
            logger.error(f"Ошибка при проверке/создании проекта в SonarQube: {e}", exc_info=True)
            raise
    
    def _run_scanner(self):
        """Запуск SonarQube Scanner для анализа проекта"""
        import subprocess
        import os
        
        logger.info("Запуск SonarQube Scanner")
        
        # Путь к SonarQube Scanner должен быть в PATH или указан явно
        try:
            # Создаем файл конфигурации sonar-project.properties
            properties_path = self.project_path / "sonar-project.properties"
            with open(properties_path, 'w') as f:
                f.write(f"sonar.projectKey={self.project_key}\n")
                f.write(f"sonar.projectName={self.project_path.name}\n")
                f.write(f"sonar.sources=.\n")
                f.write(f"sonar.sourceEncoding=UTF-8\n")
                # Добавьте другие необходимые параметры
            
            # Запускаем сканер
            result = subprocess.run(
                ["sonar-scanner"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"SonarQube Scanner завершил работу: {result.stdout}")
            
            # Удаляем временный файл конфигурации
            properties_path.unlink()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при запуске SonarQube Scanner: {e.stderr}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Ошибка при анализе проекта с SonarQube Scanner: {e}", exc_info=True)
            raise
    
    def _wait_for_analysis_completion(self, timeout: int = 300, interval: int = 10):
        """Ожидание завершения анализа проекта"""
        logger.info("Ожидание завершения анализа в SonarQube")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Получаем статус последнего анализа
                ce_activity = list(self.sonar.ce.get_ce_activity(component=self.project_key, status="IN_PROGRESS"))
                
                if not ce_activity:
                    logger.info("Анализ проекта в SonarQube завершен")
                    return
                
                logger.info(f"Анализ все еще выполняется, ожидание {interval} секунд...")
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке статуса анализа: {e}", exc_info=True)
                raise
        
        raise TimeoutError("Превышено время ожидания завершения анализа")
    
    def _get_project_data(self) -> Dict:
        """Получение данных о проекте из SonarQube"""
        logger.info("Получение данных о проекте из SonarQube")
        
        try:
            # Формируем структуру проекта
            structure = {
                'name': self.project_path.name,
                'directories': []
            }
            
            # Получаем компоненты проекта (файлы и директории)
            components = list(self.sonar.components.get_project_components(component=self.project_key))
            
            # Словарь для отслеживания директорий
            directories = {}
            
            # Сначала обрабатываем директории
            for component in components:
                if component['qualifier'] == 'DIR':
                    path = component['path'] if 'path' in component else component['name']
                    dir_data = {
                        'type': 'directory',
                        'name': Path(path).name,
                        'path': path,
                        'files': []
                    }
                    directories[component['key']] = dir_data
                    structure['directories'].append(dir_data)
            
            # Затем обрабатываем файлы
            for component in components:
                if component['qualifier'] == 'FIL':
                    file_data = self._get_file_data(component)
                    if file_data:
                        # Определяем, к какой директории относится файл
                        parent_key = self._get_parent_dir_key(component['key'])
                        if parent_key and parent_key in directories:
                            directories[parent_key]['files'].append(file_data)
                        else:
                            # Если родительская директория не найдена, добавляем файл напрямую в проект
                            structure['directories'].append(file_data)
            
            return structure
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных о проекте из SonarQube: {e}", exc_info=True)
            raise
    
    def _get_file_data(self, component: Dict) -> Optional[Dict]:
        """Получение данных о файле"""
        path = component['path'] if 'path' in component else component['name']
        file_path = Path(path)
        
        if not self._is_supported_file(file_path):
            return None
        
        logger.info(f"Анализ файла: {path}")
        
        try:
            file_data = {
                'type': 'file',
                'name': file_path.stem,
                'path': path,
                'classes': [],
                'functions': []
            }
            
            # Получаем исходный код файла
            source = self._get_file_source(component['key'])
            
            # Анализируем исходный код в зависимости от языка
            if file_path.suffix.lower() == '.py':
                self._analyze_python_file(file_data, source, component['key'])
            elif file_path.suffix.lower() in ('.java', '.kt'):
                self._analyze_java_file(file_data, source, component['key'])
            elif file_path.suffix.lower() in ('.js', '.ts'):
                self._analyze_js_file(file_data, source, component['key'])
            elif file_path.suffix.lower() in ('.cpp', '.h', '.hpp', '.cc'):
                self._analyze_cpp_file(file_data, source, component['key'])
            
            return file_data if file_data['classes'] or file_data['functions'] else None
            
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {path}: {e}", exc_info=True)
            return None
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Проверка, поддерживается ли файл для анализа"""
        return file_path.suffix.lower() in ('.py', '.java', '.kt', '.js', '.ts', '.cpp', '.h', '.hpp', '.cc')
    
    def _get_file_source(self, file_key: str) -> List[Dict]:
        """Получение исходного кода файла"""
        return list(self.sonar.sources.get_source(component=file_key))
    
    def _get_parent_dir_key(self, file_key: str) -> Optional[str]:
        """Получение ключа родительской директории"""
        parts = file_key.split(':')
        if len(parts) <= 1:
            return None
        
        # Обрезаем последнюю часть, чтобы получить ключ директории
        file_path = parts[-1]
        parent_path = str(Path(file_path).parent)
        if parent_path == '.':
            return None
            
        return f"{parts[0]}:{parent_path}"
    
    def _analyze_python_file(self, file_data: Dict, source: List[Dict], file_key: str):
        """Анализ Python файла"""
        try:
            # Получаем символы файла (классы, функции)
            symbols = list(self.sonar.measures.get_component_tree(
                component=file_key,
                metricKeys='complexity,ncloc,functions,classes',
                strategy='children'
            ))
            
            for symbol in symbols.get('components', []):
                if symbol['qualifier'] == 'CLA':  # Класс
                    class_info = self._get_python_class_info(symbol, source)
                    if class_info:
                        file_data['classes'].append(class_info)
                elif symbol['qualifier'] == 'FNC':  # Функция
                    func_info = self._get_python_function_info(symbol, source)
                    if func_info:
                        file_data['functions'].append(func_info)
                        
        except Exception as e:
            logger.error(f"Ошибка при анализе Python файла: {e}", exc_info=True)
    
    def _get_python_class_info(self, symbol: Dict, source: List[Dict]) -> Dict:
        """Получение информации о Python классе"""
        # Получаем больше информации о классе через API
        # Это упрощенная реализация, в реальности понадобится больше работы с API
        
        start_line = symbol.get('line', 1)
        end_line = start_line + 20  # Примерная оценка, в реальности нужно определять точнее
        
        class_info = {
            'type': 'class',
            'name': symbol['name'],
            'docstring': self._extract_docstring(source, start_line, end_line),
            'methods': [],
            'bases': [],  # SonarQube не дает прямого доступа к этой информации
            'source_code': self._extract_code(source, start_line, end_line),
            'line_number': start_line
        }
        
        # Получаем методы класса
        # В реальности это сложнее из-за ограничений API
        # Здесь мы просто демонстрируем подход
        
        return class_info
    
    def _get_python_function_info(self, symbol: Dict, source: List[Dict]) -> Dict:
        """Получение информации о Python функции"""
        start_line = symbol.get('line', 1)
        end_line = start_line + 10  # Примерная оценка
        
        func_info = {
            'type': 'function',
            'name': symbol['name'],
            'args': [],  # SonarQube не дает прямого доступа к этой информации
            'returns': None,  # SonarQube не дает прямого доступа к этой информации
            'docstring': self._extract_docstring(source, start_line, end_line),
            'decorators': [],  # SonarQube не дает прямого доступа к этой информации
            'source_code': self._extract_code(source, start_line, end_line),
            'line_number': start_line
        }
        
        return func_info
    
    def _extract_docstring(self, source: List[Dict], start_line: int, end_line: int) -> str:
        """Извлечение строки документации"""
        # Простая эвристика для извлечения docstring
        docstring = ""
        in_docstring = False
        
        for i in range(start_line, min(end_line, len(source))):
            line = source[i].get('code', '').strip()
            
            if line.startswith('"""') or line.startswith("'''"):
                in_docstring = not in_docstring
                line = line[3:]
                
            if in_docstring:
                docstring += line + "\n"
                
            if (line.endswith('"""') or line.endswith("'''")) and in_docstring:
                in_docstring = False
                break
                
        return docstring.strip()
    
    def _extract_code(self, source: List[Dict], start_line: int, end_line: int) -> str:
        """Извлечение исходного кода"""
        code_lines = []
        for i in range(start_line - 1, min(end_line, len(source))):
            line = source[i].get('code', '')
            code_lines.append(line)
        return "\n".join(code_lines)
    
    # Здесь будут методы для анализа других языков
    def _analyze_java_file(self, file_data: Dict, source: List[Dict], file_key: str):
        """Анализ Java файла"""
        # Аналогично _analyze_python_file, но с учетом особенностей Java
        pass
    
    def _analyze_js_file(self, file_data: Dict, source: List[Dict], file_key: str):
        """Анализ JavaScript/TypeScript файла"""
        # Аналогично _analyze_python_file, но с учетом особенностей JS/TS
        pass
    
    def _analyze_cpp_file(self, file_data: Dict, source: List[Dict], file_key: str):
        """Анализ C++ файла"""
        # Аналогично _analyze_python_file, но с учетом особенностей C++
        pass 