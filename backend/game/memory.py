from game.models import GameTurn, NPCMemory, NPCState


def remember(
    *, npc_state: NPCState, turn: GameTurn, summary: str, importance: int = 1
) -> NPCMemory:
    return NPCMemory.objects.create(
        npc_state=npc_state,
        turn=turn,
        summary=summary,
        importance=importance,
    )


def get_npc_memories(npc_state: NPCState, limit: int = 10) -> list[dict]:
    memories = NPCMemory.objects.filter(
        npc_state=npc_state,
    ).order_by("-turn__number", "-id")[:limit]

    return [
        {
            "summary": memory.summary,
            "importance": memory.importance,
        }
        for memory in memories
    ]
