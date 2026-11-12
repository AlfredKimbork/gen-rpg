import random
from dataclasses import dataclass


@dataclass(frozen=True)
class AttackResult:
    roll: int
    modifier: int
    total: int
    defense: int
    hit: bool
    damage: int


def roll_d20() -> int:
    return random.randint(1, 20)


def resolve_attack(
    *,
    strength: int,
    defense: int,
    weapon_damage: int,
) -> AttackResult:
    roll = roll_d20()
    modifier = (strength - 10) // 2
    total = roll + modifier

    # Natural 1 always misses; natural 20 always hits.
    hit = roll == 20 or (roll != 1 and total >= defense)

    damage = max(0, weapon_damage + modifier) if hit else 0

    return AttackResult(
        roll=roll,
        modifier=modifier,
        total=total,
        defense=defense,
        hit=hit,
        damage=damage,
    )
