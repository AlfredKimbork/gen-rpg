from uuid import uuid4

from django.conf import settings
from django.db import models

from characters.models import Character
from world.models import NPC, Campaign, Location, Quest


class GameSession(models.Model):
    objects = models.Manager()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_sessions",
        null=True,
        blank=True,
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.PROTECT,
        related_name="game_sessions",
    )
    current_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
    )
    flags = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default="active")
    turn_number = models.PositiveIntegerField(default=0)  # pyright: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GameTurn(models.Model):
    objects = models.Manager()
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    number = models.PositiveIntegerField()  # pyright: ignore
    action_id = models.UUIDField(default=uuid4, null=True, blank=True)

    player_action = models.TextField()
    narration = models.TextField(blank=True)
    mechanical_result = models.JSONField(default=dict)

    original_message = models.TextField(
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("number",)
        constraints = (
            models.UniqueConstraint(
                fields=["session", "number"],
                name="unique_session_turn_number",
            ),
            models.UniqueConstraint(
                fields=["session", "action_id"],
                name="unique_session_turn_action_id",
            ),
        )


class PlayerState(models.Model):
    objects = models.Manager()
    session = models.OneToOneField(
        GameSession,
        on_delete=models.CASCADE,
        related_name="player_state",
    )

    hp = models.PositiveIntegerField()
    max_hp = models.PositiveIntegerField()
    gold = models.PositiveIntegerField()
    inventory = models.JSONField(default=list, blank=True)

    def take_damage(self, amount: int) -> None:
        self.hp = max(self.hp - amount, 0)  # pyright: ignore
        self.save(update_fields=["hp"])

    def heal(self, amount: int) -> None:
        self.hp = min(self.hp + amount, self.max_hp)  # pyright: ignore
        self.save(update_fields=["hp"])

    def __str__(self):
        return f"Player state for session {self.session_id}"  # pyright: ignore


class NPCState(models.Model):
    objects = models.Manager()
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="npc_states",
    )
    npc = models.ForeignKey(
        NPC,
        on_delete=models.PROTECT,
    )
    current_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
    )
    hp = models.IntegerField()
    max_hp = models.IntegerField()
    alive = models.BooleanField(default=True)  # pyright: ignore
    trust = models.IntegerField(default=0)  # pyright: ignore
    hostility = models.IntegerField(default=0)  # pyright: ignore

    state = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["session", "npc"],
                name="unique_session_npc",
            ),
        )


class NPCMemory(models.Model):
    objects = models.Manager()
    npc_state = models.ForeignKey(
        NPCState,
        on_delete=models.CASCADE,
        related_name="memories",
    )

    turn = models.ForeignKey(
        GameTurn,
        on_delete=models.CASCADE,
        related_name="npc_memories",
    )
    summary = models.TextField()

    importance = models.IntegerField(default=1)  # pyright: ignore

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class QuestState(models.Model):
    objects = models.Manager()
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="quest_states",
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=20, default="not_started")
    completed_objectives = models.JSONField(default=list)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["session", "quest"],
                name="unique_session_quest",
            ),
        )
