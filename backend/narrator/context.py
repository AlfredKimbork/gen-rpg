from game.knowledge import get_permitted_knowledge
from game.memory import get_npc_memories
from game.models import GameSession, GameTurn, NPCState
from narrator.schemas import AIActionResponse


def build_interpreter_context(session: GameSession):
    location = session.current_location

    npcs = NPCState.objects.filter(
        session=session,
        current_location=location,
        alive=True,
    ).select_related("npc")

    return {
        "location": {
            "slug": location.slug,  # pyright: ignore
            "name": location.name,
            "description": location.description,
        },
        "connections": location.data.get("connections", []),  # pyright: ignore
        "npcs": [
            {
                "slug": npc.npc.slug,
                "name": npc.npc.name,
            }
            for npc in npcs
        ],
        "inventory": session.player_state.inventory,  # pyright: ignore
    }


def build_dialogue_context(session: GameSession, action: AIActionResponse):
    target_slug = action.target_slug

    npc_state = (
        NPCState.objects.filter(
            session=session,
            npc__slug=target_slug,
        )
        .select_related("npc")
        .first()
    )

    memories = get_npc_memories(npc_state)

    npc_data = npc_state.npc.data

    return {
        "npc": {
            "name": npc_state.npc.name,
            "personality": npc_data.get("personality", ""),
            "role": npc_data.get("role", ""),
            "hostility": npc_state.hostility,
            "trust": npc_state.trust,
        },
        "memories": memories,
        "permitted_knowledge": get_permitted_knowledge(session, npc_state),
        "player_message": action.message,
        "location": {
            "slug": session.current_location.slug,  # pyright: ignore
            "name": session.current_location.name,
        },
    }


def build_narrator_context(session: GameSession, turn: GameTurn):
    location = session.current_location

    npcs = NPCState.objects.filter(
        session=session,
        current_location=location,
    ).select_related("npc")

    visible_npcs = []

    for state in npcs:
        if not state.alive:
            continue

        npc_data = state.npc.data

        visible_npcs.append(
            {
                "slug": state.npc.slug,
                "name": state.npc.name,
                "personality": npc_data.get("personality", ""),
                "role": npc_data.get("role", ""),
                "hostility": state.hostility,
                "trust": state.trust,
                "public_knowledge": npc_data.get("public_knowledge", []),
            }
        )

    previous_turns = (
        GameTurn.objects.filter(
            session=session,
        )
        .exclude(pk=session.pk)
        .order_by("-number")
    )

    history = [
        {
            "player_action": previous.player_action,
            "narration": previous.narration,
        }
        for previous in reversed(list(previous_turns))
    ]

    return {
        "location": {
            "slug": location.slug,  # pyright: ignore
            "name": location.name,
            "description": location.description,
        },
        "npcs": visible_npcs,
        "player": {
            "inventory": session.player_state.inventory,  # pyright: ignore
            "hp": session.player_state.hp,  # pyright: ignore
            "max_hp": session.player_state.max_hp,  # pyright: ignore
        },
        "history": history,
        "action": {
            "original_message": turn.original_message,
            "player_action": turn.player_action,
            "mechanical_result": turn.mechanical_result,
        },
    }
