from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from game.actions import process_attack, process_inspect, process_movement, process_talk
from game.models import GameSession
from game.serializers import (
    AttackActionSerializer,
    CreateGameSessionSerializer,
    GameSessionSerializer,
    GameTurnSerializer,
    InspectActionSerializer,
    MoveActionSerializer,
    PlayActionSerializer,
    TalkActionSerializer,
)
from game.services import create_game_session
from narrator.services import play_turn


class GameSessionViewSet(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CreateGameSessionSerializer
    http_method_names = (
        "get",
        "post",
        "head",
        "options",
    )

    def get_queryset(self):
        return (
            GameSession.objects.filter(owner=self.request.user)
            .select_related(
                "campaign",
                "character",
                "current_location",
                "player_state",
            )
            .prefetch_related(
                "npc_states__npc",
                "npc_states__current_location",
                "quest_states__quest",
            )
            .order_by("-created_at")
        )

    def list(self, request):
        sessions = self.get_queryset()
        return Response(
            self.get_serializer(sessions, many=True).data,
        )

    def retrieve(self, request, pk=None):
        session = self.get_object()
        return Response(
            self.get_serializer(session).data,
        )

    def create(self, request):
        serializer = CreateGameSessionSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        session = create_game_session(
            owner=request.user,  # pyright: ignore
            character=serializer.validated_data["character"],  # pyright: ignore
            campaign=serializer.validated_data["campaign"],  # pyright: ignore
        )

        return Response(
            GameSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def turns(self, request, pk=None):
        session = self.get_object()

        turns = session.turns.all().order_by("number")

        return Response(
            GameTurnSerializer(turns, many=True).data,
        )

    @action(detail=True, methods=["post"])
    def actions(self, request, pk=None):
        session = self.get_object()
        action_type = request.data.get("type")

        match action_type:
            case "attack":
                serializer = AttackActionSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                data = serializer.validated_data

                turn = process_attack(
                    session=session,
                    action_id=data["action_id"],
                    target_slug=data["target_slug"],
                    weapon_slug=data["weapon_slug"],
                )

            case "move":
                serializer = MoveActionSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                data = serializer.validated_data

                turn = process_movement(
                    session=session,
                    action_id=data["action_id"],
                    destination_slug=data["destination_slug"],
                )

            case "inspect":
                serializer = InspectActionSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                data = serializer.validated_data

                turn = process_inspect(
                    session=session,
                    action_id=data["action_id"],
                )

            case "talk":
                serializer = TalkActionSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                data = serializer.validated_data

                turn = process_talk(
                    session=session,
                    action_id=data["action_id"],
                    target_slug=data["target_slug"],
                    message=data["message"],
                )
            case _:
                raise ValidationError(f"Invalid action type: {action_type}")

        return Response(
            GameTurnSerializer(turn).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def play(self, request, pk=None):
        session = self.get_object()

        serializer = PlayActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        turn = play_turn(
            session=session,
            action_id=data["action_id"],
            message=data["message"],
        )

        return Response(
            GameTurnSerializer(turn).data,
            status=status.HTTP_201_CREATED,
        )
