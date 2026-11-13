from django.db import transaction

from game.models import NPCState

RELATIONSHIP_CHANGES = {
    "helped_npc": (2, -1),
    "threatened_npc": (-2, 3),
    "insulted_npc": (-3, 2),
    "attacked_npc": (-5, 5),
    "gave_gift": (3, -1),
    "shared_secret": (2, -1),
    "revealed_secret": (-2, 3),
    "lied_to_npc": (-3, 4),
    "saved_npc": (4, -2),
    "betrayed_npc": (-5, 5),
    "stole_from_npc": (-4, 4),
    "rescued_npc": (3, -1),
    "befriended_npc": (2, -1),
    "flirted_with_npc": (2, -1),
    "romanced_npc": (3, -1),
    "ignored_npc": (-1, 1),
    "mocked_npc": (-2, 2),
    "praised_npc": (2, -1),
    "shared_personal_story": (2, -1),
    "helped_npc_in_combat": (3, -1),
    "saved_npc_from_danger": (4, -2),
    "betrayed_npc_in_combat": (-5, 5),
    "broke_promise_to_npc": (-3, 4),
    "kept_promise_to_npc": (2, -1),
    "shared_valuable_information": (3, -1),
    "revealed_valuable_information": (-2, 3),
    "shared_sensitive_information": (2, -1),
    "revealed_sensitive_information": (-2, 3),
    "helped_npc_with_personal_problem": (3, -1),
    "ignored_npc_request_for_help": (-2, 2),
    "helped_npc_with_task": (2, -1),
    "ignored_npc_request_for_task": (-1, 1),
    "helped_npc_with_quest": (3, -1),
}


@transaction.atomic
def apply_relationship_event(*, npc_state: NPCState, event: str) -> NPCState:
    if event not in RELATIONSHIP_CHANGES:
        raise ValueError(f"Unknown relationship event: {event}")

    trust_change, hostility_change = RELATIONSHIP_CHANGES[event]

    locked_state = NPCState.objects.select_for_update().get(pk=npc_state.pk)

    locked_state.trust = max(
        -100,
        min(100, locked_state.trust + trust_change),
    )

    locked_state.hostility = max(
        0,
        min(100, locked_state.hostility + hostility_change),
    )

    locked_state.save(update_fields=["trust", "hostility"])

    npc_state.trust = locked_state.trust  # pyright: ignore
    npc_state.hostility = locked_state.hostility  # pyright: ignore

    return locked_state
