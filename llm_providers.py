from abc import ABC, abstractmethod
import logging
from typing import Optional
import openai
import requests

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Абстрактный класс для провайдеров LLM"""
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """Генерация текста с помощью языковой модели"""
        pass

class OpenAIProvider(LLMProvider):
    """Провайдер для OpenAI GPT"""
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        logger.info("Инициализирован провайдер OpenAI")

    def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        try:
            logger.debug(f"Отправка запроса к OpenAI. Длина промпта: {len(prompt)} символов")
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            result = response.choices[0].message.content
            
            # Логирование результата
            logger.info(f"Получен ответ от OpenAI. Длина: {len(result)} символов")
            # Сокращаем вывод в лог для читаемости
            shortened_result = result[:100] + "..." if len(result) > 100 else result
            logger.info(f"Ответ: {shortened_result}")
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI: {e}", exc_info=True)
            return "*Не удалось сгенерировать описание*"

class OllamaProvider(LLMProvider):
    """Провайдер для локальной модели WizardCoder"""
    def __init__(self, model_name: str = "wizardcoder:7b-python", host: str = "http://localhost:8000"):
        self.model_name = model_name
        self.host = host.rstrip('/')
        self.max_context_length = 1500
        logger.info(f"Инициализирован провайдер WizardCoder с моделью {model_name}")

    def _simplify_prompt(self, prompt: str) -> str:
        """Упрощение промпта для WizardCoder"""
        # Извлекаем только самую важную информацию
        lines = prompt.strip().split("\n")
        simplified = []
        
        # Извлекаем имя и другие ключевые данные
        name = ""
        for line in lines:
            line = line.strip()
            if "Название:" in line:
                name = line.split("Название:")[1].strip()
            if not line.startswith("ВАЖНО:") and "только для анализа" not in line:
                simplified.append(line)
        
        # Создаем более простой промпт
        result = f"Опиши простыми словами, что делает Python {'класс' if 'класс' in prompt.lower() else 'функция'} '{name}'.\n\n"
        result += "\n".join(simplified)
        result += "\n\nПредоставь короткое описание без примеров кода, 2-3 предложения."
        
        return result

    def _generate_default_description(self, prompt: str) -> str:
        """Генерация стандартного описания, если модель не вернула результат"""
        # Извлекаем имя из промпта
        name = ""
        for line in prompt.split("\n"):
            if "Название:" in line:
                name = line.split("Название:")[1].strip()
                break
        
        if "класс" in prompt.lower():
            return f"Класс {name} предоставляет функциональность для обработки данных и выполнения операций, связанных с его назначением. Он инкапсулирует логику и состояние, необходимые для решения соответствующих задач."
        else:
            return f"Функция {name} обрабатывает входные данные и выполняет определенные операции в соответствии с её назначением. Она предназначена для использования в контексте, указанном в описании модуля."

    def _truncate_prompt(self, prompt: str, max_length: int = 1500) -> str:
        """Обрезка промпта до указанной длины"""
        if len(prompt) <= max_length:
            return prompt
            
        # Разделяем на части
        parts = prompt.split("```")
        if len(parts) <= 1:
            # Если нет блоков кода, просто обрезаем
            return prompt[:max_length]
            
        # Сохраняем инструкции и описание, обрезаем только код
        prelude = parts[0]
        code = parts[1] if len(parts) > 1 else ""
        suffix = "".join(parts[2:]) if len(parts) > 2 else ""
        
        # Определяем сколько места оставить для кода
        available_space = max_length - len(prelude) - len(suffix) - 6  # 6 для маркеров ```
        
        if available_space <= 0:
            # Если места не хватает, убираем весь код
            return prelude + suffix
            
        truncated_code = code[:available_space]
        
        # Собираем обратно
        if code:
            return prelude + "```" + truncated_code + "```" + suffix
        else:
            return prelude + suffix

    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            # Очищаем и упрощаем промпт для WizardCoder
            clean_prompt = self._simplify_prompt(prompt)
            
            # Обрезаем промпт до безопасной длины
            truncated_prompt = self._truncate_prompt(clean_prompt, self.max_context_length)
            
            logger.debug(f"Отправка запроса к WizardCoder ({self.model_name})")
            logger.debug(f"Длина промпта: {len(truncated_prompt)} символов")
            
            response = requests.post(
                f"{self.host}/v1/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "prompt": truncated_prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                    "model": self.model_name
                }
            )
            
            if response.status_code == 200:
                text = response.json()['choices'][0]['text']
                
                # Если ответ пустой или слишком короткий, генерируем стандартный ответ
                if not text or len(text.strip()) < 10:
                    return self._generate_default_description(truncated_prompt)
                    
                return text
            else:
                logger.error(f"Ошибка API: {response.text}")
                return self._generate_default_description(truncated_prompt)
        except Exception as e:
            logger.error(f"Ошибка при запросе к WizardCoder: {e}", exc_info=True)
            return self._generate_default_description(truncated_prompt) 