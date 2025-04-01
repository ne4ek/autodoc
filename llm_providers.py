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
        self.max_context_length = 1500  # Уменьшаем максимальную длину контекста
        logger.info(f"Инициализирован провайдер WizardCoder с моделью {model_name}")

    def _truncate_prompt(self, prompt: str, max_length: int = 1500) -> str:
        """Обрезка промпта до указанной длины"""
        words = prompt.split()
        truncated_words = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length:
                truncated_words.append(word)
                current_length += len(word) + 1
            else:
                break
                
        return ' '.join(truncated_words)

    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            # Очищаем и упрощаем промпт для WizardCoder
            clean_prompt = self._simplify_prompt(prompt)
            
            # Обрезаем промпт до безопасной длины
            truncated_prompt = self._truncate_prompt(clean_prompt, self.max_context_length)
            
            logger.debug(f"Отправка запроса к WizardCoder. Длина промпта: {len(truncated_prompt)} символов")
            # Выводим сам промпт в debug для отладки
            logger.debug(f"Промпт: {truncated_prompt[:150]}...")
            
            response = requests.post(
                f"{self.host}/v1/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "prompt": truncated_prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                    "model": self.model_name,
                    "stop": ["```"]
                }
            )
            
            if response.status_code == 200:
                text = response.json()['choices'][0]['text']
                
                # Логирование результата
                logger.info(f"Получен ответ от WizardCoder. Длина: {len(text)} символов")
                # Сокращаем вывод в лог для читаемости
                shortened_text = text[:100] + "..." if len(text) > 100 else text
                logger.info(f"Ответ: {shortened_text}")
                
                # Если ответ пустой или слишком короткий, генерируем стандартный ответ
                if not text or len(text.strip()) < 10:
                    default_text = self._generate_default_description(truncated_prompt)
                    logger.warning(f"Генерация стандартного ответа: {default_text}")
                    return default_text
                    
                return text
            else:
                error_message = f"Ошибка API: {response.text}"
                logger.error(error_message)
                default_text = self._generate_default_description(truncated_prompt)
                logger.warning(f"Генерация стандартного ответа: {default_text}")
                return default_text
        except Exception as e:
            logger.error(f"Ошибка при запросе к WizardCoder: {e}", exc_info=True)
            default_text = self._generate_default_description(truncated_prompt)
            logger.warning(f"Генерация стандартного ответа: {default_text}")
            return default_text 