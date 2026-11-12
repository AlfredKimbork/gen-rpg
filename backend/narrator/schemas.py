from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AttackAction(BaseModel):
    type: Literal["attack"]
    target_slug: str
    weapon_slug: str


class MoveAction(BaseModel):
    type: Literal["move"]
    destination_slug: str


class InspectAction(BaseModel):
    type: Literal["inspect"]


class TalkAction(BaseModel):
    type: Literal["talk"]
    target_slug: str
    message: str


GameAction = Annotated[
    AttackAction | MoveAction | InspectAction | TalkAction,
    Field(discriminator="type"),
]
