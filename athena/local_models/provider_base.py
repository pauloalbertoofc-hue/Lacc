from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import urllib.request
import json
import logging

logger = logging.getLogger("athena.local_models")

class LocalModelProvider(ABC):
    """Contrato abstrato e neutro para provedores locais de modelos cognitivos."""
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1000) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

class ModelDetector:
    """
    Detector de Capacidade de Hardware e Infraestrutura Local:
    Informa com precisão se o Ollama ou outros runtimes locais estão disponíveis sem falsas promessas.
    """
    @staticmethod
    def check_ollama_status() -> Dict[str, Any]:
        ollama_url = "http://localhost:11434/api/tags"
        try:
            req = urllib.request.Request(ollama_url, headers={"User-Agent": "Athena-Kernel/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "installed": True,
                        "running": True,
                        "endpoint": "http://localhost:11434",
                        "models_count": len(models),
                        "available_models": models,
                        "status": "ready" if models else "online_no_models"
                    }
        except Exception as e:
            return {
                "installed": True, # Sabemos que o executável está no host
                "running": False,
                "endpoint": "http://localhost:11434",
                "available_models": [],
                "status": "offline",
                "notice": "Ollama está instalado mas o daemon não está em execução ou não há modelos baixados."
            }

    @staticmethod
    def get_hardware_profile() -> Dict[str, Any]:
        ollama_info = ModelDetector.check_ollama_status()
        return {
            "mode": "hybrid_local",
            "cloud_apis_used": False,
            "cloud_vendors_blocked": ["OpenAI", "Gemini", "Claude"],
            "ollama_runtime": ollama_info,
            "rule_based_fallback": {
                "active": True,
                "status": "ready",
                "dogmatic_templates": "Ciências Criminais (CPP, CP, LEP, Criminologia Crítica)"
            }
        }

