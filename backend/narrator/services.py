import logging
from uuid import UUID

from django.apps.config import os
from django.core.exceptions import ValidationError
from rest_framework.exceptions import APIException

from game.actions import process_attack, process_inspect, process_movement, process_talk
from game.memory import remember
from game.models import GameSession, GameTurn, NPCState
from narrator.context import (
    build_dialogue_context,
    build_interpreter_context,
    build_narrator_context,
)
from narrator.providers import AIProviderError, GeminiAIProvider, MockAIProvider

logger = logging.getLogger(__name__)


def play_turn(
    *,
    session: GameSession,
    action_id: UUID,
    message: str,
    provider=None,
) -> GameTurn:
    existing = GameTurn.objects.filter(
        session=session,
        action_id=action_id,
    ).first()

    if existing:
        if existing.original_message != message:
            raise ValidationError(
                f"Existing turn with action_id {action_id} has a different original_message: {existing.original_message} vs {message}"
            )
        return existing

    if provider is None:
        if os.getenv("AI_PROVIDER", "mock") == "gemini":
            provider = GeminiAIProvider()
        else:
            provider = MockAIProvider()

    context = build_interpreter_context(session)

    try:
        action = provider.interpret(message, context)
    except AIProviderError as exc:
        raise AIUnavailable() from exc
    except ValueError as exc:
        raise ValidationError({"message": str(exc)}) from exc

    match action.type:
        case "attack":
            turn = process_attack(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                target_slug=action.target_slug,  # pyright: ignore
                weapon_slug=action.weapon_slug,  # pyright: ignore
            )

        case "move":
            turn = process_movement(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                destination_slug=action.destination_slug,  # pyright: ignore
            )

        case "inspect":
            turn = process_inspect(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
            )

        case "talk":
            turn = process_talk(
                session=session,  # pyright: ignore
                action_id=action_id,  # pyright: ignore
                target_slug=action.target_slug,  # pyright: ignore
                message=action.message,  # pyright: ignore
            )

        case _:
            raise ValidationError(f"Invalid action type: {action.type}")

    turn.original_message = message  #   pyright: ignore
    turn.save(update_fields=["original_message"])  #  pyright: ignore

    session.refresh_from_db()  # pyright: ignore

    if action.type == "talk":
        dialogue_context = build_dialogue_context(
            session,
            action,  #   pyright: ignore
        )

        try:
            dialogue = provider.generate_dialogue(dialogue_context)  # pyright: ignore
        except AIProviderError:
            logger.exception("AI provider error during dialogue generation")
            dialogue = "I have nothing to say right now"  # pyright: ignore

        result = turn.mechanical_result  # pyright: ignore
        result["response"] = dialogue  # pyright: ignore

        npc_state = NPCState.objects.get(
            session=session,
            npc__slug=action.target_slug,  # pyright: ignore
        )
        remember(
            npc_state=npc_state,  #  pyright: ignore
            turn=turn,  # pyright: ignore
            summary=(
                f"Player asked: {action.message}. "
                f"{npc_state.npc.name} replied: {dialogue}"
            ),
            importance=2,
        )

    if hasattr(provider, "narrate"):
        narration_context = build_narrator_context(session, turn)  # pyright: ignore

        try:
            narration = provider.narrate(narration_context)  # pyright: ignore

        except AIProviderError:
            logger.exception("AI provider error during narration")
            narration = turn.narration  # pyright: ignore

        turn.narration = narration  # pyright: ignore
        turn.save(update_fields=["narration"])  # pyright: ignore

    return turn  # pyright: ignore


class AIUnavailable(APIException):
    status_code = 503
    default_detail = "AI interpreter is unavailable. Please try again later."
    default_code = "ai_unavailable"
