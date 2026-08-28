from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger("athena.event_bus")

class CognitiveEventBus:
    """Barramento de eventos síncrono para o ciclo cognitivo da Athena."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[str, Dict[str, Any]], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event_type, payload)
            except Exception as e:
                logger.error(f"Erro ao processar evento {event_type}: {e}")

event_bus = CognitiveEventBus()

