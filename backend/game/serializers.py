from uuid import uuid4

from rest_framework import serializers

from world.models import Campaign

from .models import Character, GameSession, GameTurn, NPCState, QuestState


class CreateGameSessionSerializer(serializers.Serializer):
    character_id = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(),
        source="character",
    )
    campaign_id = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.all(),
        source="campaign",
    )

    def validate(self, attrs):
        request = self.context.get("request")
        character = attrs.get("character")

        if character.owner_id != request.user.id:  # pyright: ignore
            raise serializers.ValidationError(
                {"character_id": "Character does not belong to the user."}
            )

        return attrs


class PlayerStateSerializer(serializers.Serializer):
    hp = serializers.IntegerField()
    max_hp = serializers.IntegerField()
    gold = serializers.IntegerField()
    inventory = serializers.JSONField()


class NPCStateSerializer(serializers.Serializer):
    npc_id = serializers.CharField(source="npc.id", read_only=True)
    name = serializers.CharField(source="npc.name", read_only=True)
    location = serializers.CharField(source="current_location.name", read_only=True)

    class Meta:
        model = NPCState
        fields = (
            "npc_id",
            "name",
            "location",
            "hp",
            "max_hp",
            "alive",
            "trust",
            "hostility",
        )


class QuestStateSerializer(serializers.Serializer):
    quest_id = serializers.CharField(source="quest.id", read_only=True)
    title = serializers.CharField(source="quest.title", read_only=True)

    class Meta:
        model = QuestState
        fields = (
            "quest_id",
            "title",
            "status",
            "completed_objectives",
        )


class GameSessionSerializer(serializers.Serializer):
    campaign = serializers.CharField(source="campaign.slug", read_only=True)
    character_id = serializers.IntegerField(read_only=True)
    location = serializers.CharField(source="current_location.name", read_only=True)
    player = PlayerStateSerializer(source="player_state", read_only=True)
    npcs = NPCStateSerializer(source="npc_states", many=True, read_only=True)
    quests = QuestStateSerializer(source="quest_states", many=True, read_only=True)

    class Meta:
        model = GameSession
        fields = (
            "id",
            "campaign",
            "character_id",
            "location",
            "flags",
            "status",
            "turn_number",
            "player",
            "npcs",
            "quests",
            "created_at",
            "updated_at",
        )


class GameTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameTurn
        fields = (
            "id",
            "number",
            "action_id",
            "player_action",
            "narration",
            "mechanical_result",
            "created_at",
        )
        read_only_fields = fields


class AttackActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField(default=uuid4)
    type = serializers.CharField(default="attack")
    target = serializers.SlugField(source="target_slug")
    weapon = serializers.SlugField(source="weapon_slug")


class MoveActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField(default=uuid4)
    type = serializers.CharField(default="move")
    destination = serializers.SlugField(source="destination_slug")


class InspectActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField(default=uuid4)
    type = serializers.CharField(default="inspect")


class TalkActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField(default=uuid4)
    type = serializers.CharField(default="talk")
    target = serializers.SlugField(source="target_slug")
    message = serializers.CharField(
        min_length=1,
        max_length=1000,
        trim_whitespace=True,
    )


class PlayActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField(default=uuid4)
    message = serializers.CharField(
        min_length=1,
        max_length=2000,
        trim_whitespace=True,
    )
