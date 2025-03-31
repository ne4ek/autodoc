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
            logger.debug("Отправка запроса к OpenAI")
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            logger.debug("Получен ответ от OpenAI")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI: {e}", exc_info=True)
            return "*Не удалось сгенерировать описание*"

class OllamaProvider(LLMProvider):
    """Провайдер для локальной модели WizardCoder"""
    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host.rstrip('/')
        logger.info(f"Инициализирован провайдер WizardCoder")

    def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        try:
            logger.debug(f"Отправка запроса к WizardCoder")
            response = requests.post(
                f"{self.host}/v1/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                }
            )
            
            if response.status_code == 200:
                logger.debug("Получен ответ от WizardCoder")
                return response.json()['choices'][0]['text']
            else:
                raise Exception(f"Ошибка API: {response.text}")
        except Exception as e:
            logger.error(f"Ошибка при запросе к WizardCoder: {e}", exc_info=True)
            return "*Не удалось сгенерировать описание*" 