from game.models import GameSession, NPCState


def get_permitted_knowledge(session: GameSession, npc_state: NPCState) -> list[str]:
    npc_data = npc_state.npc.data  # pyright: ignore

    permitted = list(npc_data.get("public_knowledge", []))

    for entry in npc_data.get("knowledge", []):
        conditions = entry.get("conditions", {})

        if npc_state.trust < conditions.get("min_trust", 0):
            continue

        if npc_state.hostility > conditions.get("max_hostility", 100):
            continue

        required_flags = conditions.get("required_flags", [])

        if not all(
            session.flags.get(flag, False)  # pyright: ignore
            for flag in required_flags
        ):
            continue

        permitted.append(entry["text"])

    return permitted
