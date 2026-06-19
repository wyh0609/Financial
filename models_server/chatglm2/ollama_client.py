import os
import requests
import re


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")


class OllamaClient:
    def __init__(self, model=None, base_url=None):
        self.model = model or MODEL_NAME
        self.base_url = base_url or OLLAMA_URL

    def generate(self, prompt, temperature=0.01, top_p=0.95):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p},
        }

        resp = requests.post(self.base_url, json=payload, timeout=300, proxies={"http": None, "https": None})
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("response", "")
        raw = self._clean(raw)
        return raw

    @staticmethod
    def _clean(text):
        if "</think>" in text:
            text = text.rsplit(" response", 1)[-1]
        text = re.sub(r"<\/?think>", "", text)
        text = re.sub(r"<\/?response>", "", text)
        return text.strip()