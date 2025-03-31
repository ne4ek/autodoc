import ast
from pathlib import Path
from typing import Dict, List, Optional

class ProjectAnalyzer:
    """Анализатор структуры Python проекта"""
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.ignore_dirs = {'.venv', '__pycache__', 'site-packages', '.git', '.idea'}
        
    def analyze(self) -> Dict:
        """Анализ всей структуры проекта"""
        structure = {'name': self.project_path.name, 'directories': []}
        
        for item in self.project_path.iterdir():
            if item.is_dir() and item.name not in self.ignore_dirs:
                dir_structure = self._analyze_directory(item)
                if dir_structure:
                    structure['directories'].append(dir_structure)
            elif item.suffix == '.py' and item.name != '__init__.py':
                file_structure = self._analyze_file(item)
                if file_structure:
                    structure['directories'].append(file_structure)
        
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

    def _analyze_file(self, file_path: Path) -> Optional[Dict]:
        """Анализ Python файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
            
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
                    class_info = self._analyze_class(node)
                    file_data['classes'].append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    if not hasattr(node, 'parent') or not isinstance(node.parent, ast.ClassDef):
                        func_info = self._analyze_function(node)
                        file_data['functions'].append(func_info)
            
            return file_data if file_data['classes'] or file_data['functions'] else None
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def _analyze_class(self, class_node: ast.ClassDef) -> Dict:
        """Анализ класса"""
        class_info = {
            'type': 'class',
            'name': class_node.name,
            'docstring': ast.get_docstring(class_node) or '',
            'methods': [],
            'bases': [ast.unparse(base) for base in class_node.bases]
        }
        
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = self._analyze_function(node)
                class_info['methods'].append(method_info)
        
        return class_info

    def _analyze_function(self, func_node: ast.FunctionDef) -> Dict:
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
            'decorators': [ast.unparse(decorator) for decorator in func_node.decorator_list]
        }

    # ... existing code for _analyze_directory, _analyze_file, _analyze_class, _analyze_function ... 