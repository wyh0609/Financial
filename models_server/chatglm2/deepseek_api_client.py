import os
import requests


def get_env(key, default=""):
    return os.environ.get(key, default)


class DeepSeekApiClient:
    def __init__(self, api_key=None, model=None, base_url=None):
        self.api_key = api_key or get_env("DEEPSEEK_API_KEY", "")
        self.model = model or get_env("DEEPSEEK_MODEL", "wyh")
        self.base_url = base_url or get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")

    def generate(self, prompt, temperature=0.01, top_p=0.95):
        import sys
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的金融财报分析助手，请根据提供的财报数据准确回答问题。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": 4096,
        }

        print(f"[DeepSeekAPI] Requesting {self.base_url} with model {self.model}", flush=True)
        sys.stdout.flush()
        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=300)
        print(f"[DeepSeekAPI] Response status: {resp.status_code}", flush=True)
        sys.stdout.flush()
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
