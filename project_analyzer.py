import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ProjectAnalyzer:
    """Анализатор структуры Python проекта"""
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.ignore_dirs = {'.venv', '__pycache__', 'site-packages', '.git', '.idea'}
        logger.info(f"Инициализация анализатора проекта: {project_path}")
        
    def analyze(self) -> Dict:
        """Анализ всей структуры проекта"""
        logger.info("Начало анализа структуры проекта")
        structure = {'name': self.project_path.name, 'directories': []}
        
        for item in self.project_path.iterdir():
            if item.is_dir() and item.name not in self.ignore_dirs:
                logger.info(f"Анализ директории: {item}")
                dir_structure = self._analyze_directory(item)
                if dir_structure:
                    structure['directories'].append(dir_structure)
            elif item.suffix == '.py' and item.name != '__init__.py':
                logger.info(f"Анализ файла: {item}")
                file_structure = self._analyze_file(item)
                if file_structure:
                    structure['directories'].append(file_structure)
        
        logger.info("Анализ структуры проекта завершен")
        return structure

    def _analyze_directory(self, directory: Path) -> Optional[Dict]:
        """Анализ директории"""
        dir_data = {
            'type': 'directory',
            'name': directory.name,
            'path': str(directory.relative_to(self.project_path)),
            'files': []
        }
        
        for item in directory.iterdir():
            if item.is_file() and item.suffix == '.py':
                file_data = self._analyze_file(item)
                if file_data:
                    dir_data['files'].append(file_data)
        
        return dir_data if dir_data['files'] else None

    def _get_source_code(self, node: ast.AST, source_lines: List[str]) -> str:
        """Получение исходного кода узла AST"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            # Получаем строки кода для узла
            code_lines = source_lines[node.lineno - 1:node.end_lineno]
            # Убираем лишние отступы
            min_indent = min(len(line) - len(line.lstrip()) for line in code_lines if line.strip())
            code_lines = [line[min_indent:] if line.strip() else '' for line in code_lines]
            return '\n'.join(code_lines)
        return ""

    def _analyze_file(self, file_path: Path) -> Optional[Dict]:
        """Анализ Python файла"""
        logger.info(f"Анализ файла: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                source_lines = source.splitlines()
                tree = ast.parse(source, filename=str(file_path))
            
            # Добавляем parent ссылки для всех узлов
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child.parent = node
            
            file_data = {
                'type': 'file',
                'name': file_path.stem,
                'path': str(file_path.relative_to(self.project_path)),
                'classes': [],
                'functions': []
            }
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node, source_lines)
                    file_data['classes'].append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    if not hasattr(node, 'parent') or not isinstance(node.parent, ast.ClassDef):
                        func_info = self._analyze_function(node, source_lines)
                        file_data['functions'].append(func_info)
            
            logger.debug(f"Найдено классов: {len(file_data['classes'])}, функций: {len(file_data['functions'])}")
            return file_data if file_data['classes'] or file_data['functions'] else None
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {file_path}: {e}", exc_info=True)
            return None

    def _analyze_class(self, class_node: ast.ClassDef, source_lines: List[str]) -> Dict:
        """Анализ класса"""
        class_info = {
            'type': 'class',
            'name': class_node.name,
            'docstring': ast.get_docstring(class_node) or '',
            'methods': [],
            'bases': [ast.unparse(base) for base in class_node.bases],
            'source_code': self._get_source_code(class_node, source_lines)
        }
        
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = self._analyze_function(node, source_lines)
                class_info['methods'].append(method_info)
        
        return class_info

    def _analyze_function(self, func_node: ast.FunctionDef, source_lines: List[str]) -> Dict:
        """Анализ функции/метода"""
        args = []
        for arg in func_node.args.args:
            arg_info = {
                'name': arg.arg,
                'type': ast.unparse(arg.annotation) if arg.annotation else None
            }
            args.append(arg_info)
        
        return_type = ast.unparse(func_node.returns) if func_node.returns else None
        
        return {
            'type': 'function',
            'name': func_node.name,
            'args': args,
            'returns': return_type,
            'docstring': ast.get_docstring(func_node) or '',
            'decorators': [ast.unparse(decorator) for decorator in func_node.decorator_list],
            'source_code': self._get_source_code(func_node, source_lines)
        }