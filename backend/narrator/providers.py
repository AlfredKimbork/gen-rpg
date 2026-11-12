from pydantic import TypeAdapter

from narrator.schemas import GameAction

action_adapter = TypeAdapter(GameAction)


class MockAIProvider:
    def interpret(
        self,
        message: str,
        context: dict,
    ):
        text = message.lower()

        if "attack" in text:
            npcs = context.get("npcs", [])

            if not npcs:
                raise ValueError("No NPCs available to attack.")

            return action_adapter.validate_python(
                {
                    "type": "attack",
                    "target_slug": npcs[0].slug,
                    "weapon_slug": "rusty_sword",
                }
            )
        if "move" in text or "go to" in text:
            connections = context.get("connections", [])

            if not connections:
                raise ValueError("No connections available to move to.")

            return action_adapter.validate_python(
                {
                    "type": "move",
                    "destination_slug": connections[0].slug,
                }
            )

        if "talk" in text or "say" in text or "ask" in text:
            npcs = context.get("npcs", [])

            if not npcs:
                raise ValueError("No NPCs available to talk to.")

            return action_adapter.validate_python(
                {
                    "type": "talk",
                    "target_slug": npcs[0]["slug"],
                    "message": message,
                }
            )

        return action_adapter.validate_python(
            {
                "type": "inspect",
            }
        )
