from typing import Dict, List, Any, Optional
from athena.domain.enums import MemoryType, MemoryScope, DutyScope
from athena.domain.context import ExecutionContext
from athena.persistence.athena_db import AthenaRepository

class MemoryManager:
    """
    Gestor de Memória em Camadas e com Escopo Estrito.
    Garante que membros de Comunicação não acessem memórias privadas de Tesouraria.
    """
    def __init__(self):
        # Working memory transitória em memória RAM durante o ciclo da Task
        self._working_memory: Dict[str, Dict[str, Any]] = {}

    # ==========================================
    # WORKING MEMORY (TEMPORÁRIA DA TASK)
    # ==========================================
    def set_working(self, task_id: str, key: str, value: Any):
        if task_id not in self._working_memory:
            self._working_memory[task_id] = {}
        self._working_memory[task_id][key] = value

    def get_working(self, task_id: str, key: str, default: Any = None) -> Any:
        return self._working_memory.get(task_id, {}).get(key, default)

    def clear_working(self, task_id: str):
        if task_id in self._working_memory:
            del self._working_memory[task_id]

    # ==========================================
    # PERSISTED MEMORY (SESSÃO, PROJETO, INSTITUCIONAL)
    # ==========================================
    def store_memory(
        self,
        memory_type: MemoryType,
        scope: MemoryScope,
        key: str,
        content: Dict[str, Any],
        context: ExecutionContext
    ):
        dept = context.duty_scope.value if scope == MemoryScope.DEPARTMENT else None
        owner_id = context.user_id if scope == MemoryScope.USER else None

        AthenaRepository.save_memory(
            memory_type=memory_type.value,
            scope=scope.value,
            memory_key=key,
            content=content,
            owner_id=owner_id,
            department=dept
        )

    def recall_authorized_memories(self, context: ExecutionContext, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera memórias permitidas para o contexto atual do usuário."""
        results = []
        
        # 1. Memórias Institucionais / Públicas (Acesso Geral)
        inst_mems = AthenaRepository.get_memories_for_scope(scope="institution", limit=limit)
        results.extend(inst_mems)

        # 2. Memórias do Departamento do Usuário (se houver)
        if context.duty_scope != DutyScope.GENERAL:
            dept_mems = AthenaRepository.get_memories_for_scope(
                scope="department",
                department=context.duty_scope.value,
                limit=limit
            )
            results.extend(dept_mems)

        # 3. Memórias Pessoais do Usuário
        user_mems = AthenaRepository.get_memories_for_scope(
            scope="user",
            owner_id=context.user_id,
            limit=limit
        )
        results.extend(user_mems)

        return results

memory_manager = MemoryManager()

