from game.models import GameSession, NPCState


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
