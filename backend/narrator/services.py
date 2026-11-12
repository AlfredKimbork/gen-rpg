from uuid import UUID

from django.core.exceptions import ValidationError

from game.actions import process_attack, process_inspect, process_movement, process_talk
from game.models import GameSession
from narrator.context import build_interpreter_context
from narrator.providers import MockAIProvider


def play_turn(
    *,
    session: GameSession,
    action_id: UUID,
    message: str,
    provider=None,
):
    provider = provider or MockAIProvider()

    context = build_interpreter_context(session)

    try:
        action = provider.interpret(message=message, context=context)
    except ValueError as exc:
        raise ValidationError(f"Failed to interpret message: {exc}") from exc

    match action.type:
        case "attack":
            return process_attack(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                target_slug=action.target_slug,  # pyright: ignore
                weapon_slug=action.weapon_slug,  # pyright: ignore
            )

        case "move":
            return process_movement(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                destination_slug=action.destination_slug,  # pyright: ignore
            )

        case "inspect":
            return process_inspect(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
            )

        case "talk":
            return process_talk(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                target_slug=action.target_slug,  # pyright: ignore
                message=action.message,  # pyright: ignore
            )
        case _:
            raise ValidationError(f"Invalid action type: {action.type}")
