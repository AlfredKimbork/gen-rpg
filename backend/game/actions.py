from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from game.mechanics import resolve_attack
from game.models import GameSession, GameTurn, NPCState
from game.turns import create_turn, get_existing_turn
from world.models import Location


@transaction.atomic
def process_attack(
    *,
    session: GameSession,
    action_id: UUID,
    target_slug: str,
    weapon_slug: str,
) -> GameTurn:
    # Lock the session to serialize actions within the playthrough
    session = GameSession.objects.select_for_update().get(pk=session.pk)

    existing = get_existing_turn(
        session=session,
        action_id=action_id,
        action_type="attack",
        payload={
            "target": target_slug,
            "weapon": weapon_slug,
        },
    )

    if existing:
        return existing

    if session.status != "active":
        raise ValidationError("Cannot process action for an inactive session.")

    player = session.player_state  # pyright: ignore

    if player.hp <= 0:  # pyright: ignore
        raise ValidationError("Cannot process action for a dead character.")

    target = (
        NPCState.objects.select_for_update()
        .select_related("npc", "current_location")
        .filter(
            session=session,
            npc__slug=target_slug,
        )
        .first()
    )

    if target is None:
        raise ValidationError(f"Target NPC '{target_slug}' not found in the session.")

    if target.current_location_id != session.current_location_id:  # pyright: ignore
        raise ValidationError(
            f"Target NPC '{target_slug}' is not in the same location as the player."
        )

    if not target.alive or target.hp <= 0:
        raise ValidationError(f"Target NPC '{target_slug}' is already dead.")

    # Inventory entries are assumed to be in item slugs
    if weapon_slug not in player.inventory:  # pyright: ignore
        raise ValidationError(
            f"Player does not have weapon '{weapon_slug}' in inventory."
        )

    # Temporary weapon rules for the MVP
    weapon_damage = {
        "rusty_sword": 5,
        "hunting_bow": 4,
    }.get(weapon_slug)

    if weapon_damage is None:
        raise ValueError(f"Weapon '{weapon_slug}' is not a valid weapon.")

    defense = target.state.get("defense", 10)

    result = resolve_attack(
        strength=session.character.strength,  # pyright: ignore
        weapon_damage=weapon_damage,
        defense=defense,
    )

    target.hp = max(0, target.hp - result.damage)
    target.alive = target.hp > 0
    target.hostility = max(target.hostility, 1)
    target.save(update_fields=["hp", "alive", "hostility"])

    narration = (
        f"You attack {target.npc.name} with your {weapon_slug.replace('_', ' ')}. "
    )

    if result.hit:
        narration += (
            f"You hit for {result.damage} damage! "
            f"{target.npc.name} has {target.hp} HP remaining. "
        )
    else:
        narration += f"You miss! {target.npc.name} has {target.hp} HP remaining. "

    return create_turn(
        session=session,
        action_id=action_id,
        player_action=f"Attack {target_slug} with {weapon_slug}",
        narration=narration,
        mechanical_result={
            "type": "attack",
            "target": target_slug,
            "weapon": weapon_slug,
        },
    )


@transaction.atomic
def process_movement(
    *,
    session: GameSession,
    action_id: UUID,
    destination_slug: str,
) -> GameTurn:
    # Lock the session to serialize actions within the playthrough
    session = (
        GameSession.objects.select_for_update()
        .select_related("current_location")
        .get(pk=session.pk)
    )

    existing = get_existing_turn(
        session=session,
        action_id=action_id,
        action_type="move",
        payload={
            "destination": destination_slug,
        },
    )

    if existing:
        return existing

    if session.status != "active":
        raise ValidationError("Cannot process action for an inactive session.")

    if session.player_state.hp <= 0:  # pyright: ignore
        raise ValidationError("Cannot process action for a dead character.")

    current = session.current_location
    connections = current.data.get("connections", [])  # pyright: ignore

    if destination_slug not in connections:
        raise ValidationError(
            f"Destination location '{destination_slug}' is not connected to the current location '{current.name}'."
        )

    destination = Location.objects.filter(
        campaign=session.campaign,
        slug=destination_slug,
    ).first()

    if destination is None:
        raise ValidationError(
            f"Destination location '{destination_slug}' not found in the campaign."
        )

    session.current_location = destination  # pyright: ignore
    session.save(update_fields=["current_location", "updated_at"])

    narration = f"You travel from {current.name} to {destination.name}."

    return create_turn(
        session=session,
        action_id=action_id,
        player_action=f"Move to {destination_slug}",
        narration=narration,
        mechanical_result={
            "type": "move",
            "from": current.slug,  # pyright: ignore
            "destination": destination.slug,  # pyright: ignore
        },
    )


@transaction.atomic
def process_inspect(
    *,
    session: GameSession,
    action_id: UUID,
) -> GameTurn:
    session = (
        GameSession.objects.select_for_update()
        .select_related("current_location")
        .get(pk=session.pk)
    )

    existing = get_existing_turn(
        session=session,
        action_id=action_id,
        action_type="inspect",
        payload={},
    )

    if existing:
        return existing

    if session.status != "active":
        raise ValidationError("Cannot process action for an inactive session.")

    if session.player_state.hp <= 0:  # pyright: ignore
        raise ValidationError("Cannot process action for a dead character.")

    location = session.current_location

    npcs = NPCState.objects.filter(
        session=session,
        current_location=location,
        alive=True,
    ).select_related("npc")

    visible_npcs = [
        {
            "slug": npc.npc.slug,
            "name": npc.npc.name,
            "hp": npc.hp,
            "max_hp": npc.max_hp,
            "alive": npc.alive,
            "trust": npc.trust,
            "hostility": npc.hostility,
        }
        for npc in npcs
    ]

    connections = location.data.get("connections", [])  # pyright: ignore
    interactables = location.data.get("interactables", [])  # pyright: ignore

    narration = f"You look around {location.name}. {location.description} "

    if visible_npcs:
        npc_names = ", ".join(npc["name"] for npc in visible_npcs)
        narration += f"You notice {npc_names} nearby."

    return create_turn(
        session=session,
        action_id=action_id,
        player_action="Inspect surroundings",
        narration=narration,
        mechanical_result={
            "type": "inspect",
            "location": {
                "slug": location.slug,  # pyright: ignore
                "name": location.name,  # pyright: ignore
                "description": location.description,  # pyright: ignore
            },
            "npcs": visible_npcs,
            "connections": connections,
            "interactables": interactables,
        },
    )


def get_dialogue_response(npc_data: dict) -> str:
    examples = npc_data.get("examples", [])

    if examples:
        example = examples[0]

        if isinstance(example, str):
            return example

        if isinstance(example, dict):
            return str(
                example.get("response")
                or example.get("text")
                or "I have nothing to say."
            )

    return "I have nothing to say about that right now."


@transaction.atomic
def process_talk(
    *,
    session: GameSession,
    action_id: UUID,
    target_slug: str,
    message: str,
) -> GameTurn:
    session = (
        GameSession.objects.select_for_update()
        .select_related("current_location")
        .get(pk=session.pk)
    )

    existing = get_existing_turn(
        session=session,
        action_id=action_id,
        action_type="talk",
        payload={
            "target": target_slug,
            "message": message,
        },
    )

    if existing:
        return existing

    if session.status != "active":
        raise ValidationError("Cannot process action for an inactive session.")

    if session.player_state.hp <= 0:  # pyright: ignore
        raise ValidationError("Cannot process action for a dead character.")

    npc_state = (
        NPCState.objects.select_for_update()
        .select_related("npc")
        .filter(
            session=session,
            npc__slug=target_slug,
            current_location=session.current_location,
            alive=True,
        )
        .first()
    )

    if npc_state is None:
        raise ValidationError(f"Target NPC '{target_slug}' not found in the session.")

    narration = f"You speak to {npc_state.npc.name}."

    return create_turn(
        session=session,
        action_id=action_id,
        player_action=f"Talk to {target_slug}: {message}",
        narration=narration,
        mechanical_result={
            "type": "talk",
            "target": target_slug,
            "message": message,
            "npc_name": npc_state.npc.name,
            "npc_trust": npc_state.trust,
            "npc_hostility": npc_state.hostility,
        },
    )
