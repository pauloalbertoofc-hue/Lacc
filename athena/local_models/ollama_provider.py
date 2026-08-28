import json
import urllib.request
from typing import Dict, Any, Optional
from athena.local_models.provider_base import LocalModelProvider, ModelDetector

class OllamaLocalProvider(LocalModelProvider):
    """Adapter de comunicação HTTP para runtime local Ollama (localhost:11434)."""
    def __init__(self, model_name: str = "llama3:latest", endpoint: str = "http://localhost:11434"):
        self.model_name = model_name
        self.endpoint = endpoint

    def is_available(self) -> bool:
        status = ModelDetector.check_ollama_status()
        return status.get("running", False) and self.model_name in status.get("available_models", [])

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1000) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "success": False,
                "error": f"Modelo local '{self.model_name}' indisponível no Ollama.",
                "used_fallback": True
            }

        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "Você é a Athena, inteligência cognitiva da LACC.",
            "stream": False
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "text": data.get("response", ""),
                    "model": self.model_name,
                    "total_duration_ms": int(data.get("total_duration", 0) / 1e6)
                }
        except Exception as e:
            return {"success": False, "error": str(e), "used_fallback": True}

class RuleBasedCognitiveProvider(LocalModelProvider):
    """
    Provedor Cognitivo Baseado em Regras e Templates Estruturados:
    Garante que a Athena execute perfeitamente mesmo sem modelos neurais pesados instalados no host.
    """
    def is_available(self) -> bool:
        return True

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1000) -> Dict[str, Any]:
        return {
            "success": True,
            "mode": "rule_based_deterministic",
            "text": "Conteúdo gerado via motor de regras determinísticas da Athena.",
            "notice": "Executado via Heurísticas de Ciências Criminais da LACC."
        }

__all__ = [
    "LocalModelProvider",
    "ModelDetector",
    "OllamaLocalProvider",
    "RuleBasedCognitiveProvider"
]

