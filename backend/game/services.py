from copy import deepcopy

from django.db import transaction

from characters.models import Character
from world.models import NPC, Campaign, Location, Quest

from .models import GameSession, NPCState, PlayerState, QuestState


@transaction.atomic
def create_game_session(
    *,
    owner,
    character: Character,
    campaign: Campaign,
) -> GameSession:

    # A user cannot start a game using another user's character
    if character.owner != owner:
        raise ValueError("Character does not belong to the user.")

    starting_state = campaign.data.get("starting_state", {})  # pyright: ignore
    starting_location_slug = starting_state.get("location")

    if not starting_location_slug:
        raise ValueError("Campaign does not have a starting location defined.")

    starting_location = Location.objects.get(
        campaign=campaign,
        slug=starting_location_slug,
    )

    session = GameSession.objects.create(
        owner=owner,
        character=character,
        campaign=campaign,
        current_location=starting_location,
        flags=deepcopy(starting_state.get("flags", {})),
        status="active",
        turn_number=0,
    )

    # each session gets it's own player state
    PlayerState.objects.create(
        session=session,
        hp=character.hp,
        max_hp=character.max_hp,
        gold=character.gold,
        inventory=deepcopy(character.inventory),
    )

    # copy the NPC's starting state into this session
    npc_states = []

    for npc in NPC.objects.filter(campaign=campaign):
        initial = npc.data.get("initial_state", {})

        npc_states.append(
            NPCState(
                session=session,
                npc=npc,
                current_location=npc.starting_location,
                hp=initial.get("hp", 10),
                max_hp=initial.get("max_hp", 10),
                alive=initial.get("alive", True),
                trust=initial.get("trust", 0),
                hostility=initial.get("hostility", 0),
                state=deepcopy(initial),
            )
        )

    NPCState.objects.bulk_create(npc_states)

    # initialize quests
    QuestState.objects.bulk_create(
        [
            QuestState(
                session=session,
                quest=quest,
                status="not_started",
                completed_objectives=[],
            )
            for quest in Quest.objects.filter(campaign=campaign).filter(
                campaign=campaign
            )
        ]
    )

    return session
