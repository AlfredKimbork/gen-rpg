from django.conf import settings
from django.db import models


class Character(models.Model):
    objects = models.Manager()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="characters",
    )
    name = models.CharField(max_length=100)
    character_class = models.CharField(
        max_length=50,
        default="Fighter",
    )

    level = models.PositiveIntegerField(default=1)  # pyright: ignore
    experience = models.PositiveIntegerField(default=0)  # pyright: ignore

    hp = models.PositiveIntegerField(default=10)  # pyright: ignore
    max_hp = models.PositiveIntegerField(default=10)  # pyright: ignore

    strength = models.PositiveIntegerField(default=10)  # pyright: ignore
    dexterity = models.PositiveIntegerField(default=10)  # pyright: ignore
    constitution = models.PositiveIntegerField(default=10)  # pyright: ignore
    intelligence = models.PositiveIntegerField(default=10)  # pyright: ignore
    wisdom = models.PositiveIntegerField(default=10)  # pyright: ignore
    charisma = models.PositiveIntegerField(default=10)  # pyright: ignore

    gold = models.PositiveIntegerField(default=0)  # pyright: ignore

    inventory = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Level {self.level} {self.character_class})"

    def attribute_modifier(self, attribute: str) -> int:
        allowed = {
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        }

        if attribute not in allowed:
            raise ValueError(f"Invalid attribute: {attribute}")

        score = getattr(self, attribute)
        return (score - 10) // 2

    def take_damage(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Damage amount cannot be negative")
        self.hp = max(self.hp - amount, 0)  # pyright: ignore
        self.save(update_fields=["hp"])

    def heal(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Heal amount cannot be negative")
        self.hp = min(self.hp + amount, self.max_hp)  # pyright: ignore
        self.save(update_fields=["hp"])
