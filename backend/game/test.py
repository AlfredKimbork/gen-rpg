from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from characters.models import Character
from game.knowledge import get_permitted_knowledge
from game.mechanics import resolve_attack
from game.models import GameTurn, NPCState, PlayerState, QuestState
from game.relationships import apply_relationship_event
from narrator.providers import GeminiAIProvider
from world.models import NPC, Campaign, Location, Quest

from .services import create_game_session

User = get_user_model()


class GameSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.location = Location.objects.create(
            campaign=self.campaign, slug="tavern", name="The Tavern"
        )

        self.npc = NPC.objects.create(
            campaign=self.campaign,
            slug="garrick",
            name="Garrick",
            starting_location=self.location,
            data={
                "initial_state": {
                    "hp": 18,
                    "max_hp": 18,
                    "alive": True,
                    "trust": 0,
                    "hostility": 0,
                },
            },
        )

        self.quest = Quest.objects.create(
            campaign=self.campaign,
            slug="first_quest",
            title="The First Quest",
        )

        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def test_creates_complete_session(self):
        session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

        self.assertEqual(session.current_location, self.location)  # pyright: ignore
        self.assertEqual(session.flags, {"quest_started": False})  # pyright: ignore

        player = PlayerState.objects.get(session=session)
        self.assertEqual(player.hp, 20)
        self.assertEqual(player.gold, 10)

        self.assertEqual(
            NPCState.objects.filter(session=session, npc=self.npc).count(), 1
        )
        self.assertEqual(
            QuestState.objects.filter(session=session, quest=self.quest).count(), 1
        )

    def test_session_have_independent_npc_states(self):
        first = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

        second = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

        first_npc = NPCState.objects.get(
            session=first,
            npc=self.npc,
        )

        first_npc.hp = 5
        first_npc.save(update_fields=["hp"])

        second_npc = NPCState.objects.get(
            session=second,
            npc=self.npc,
        )

        self.assertEqual(first_npc.hp, 5)
        self.assertEqual(second_npc.hp, 18)  # initial state from NPC data

    def test_cannot_use_another_users_character(self):
        other_user = User.objects.create_user(
            username="otherplayer",
            password="otherpassword",
        )

        with self.assertRaises(ValueError):
            create_game_session(
                owner=other_user,  # pyright: ignore
                character=self.character,  # pyright: ignore
                campaign=self.campaign,  # pyright: ignore
            )

    def test_duplicate_play_returns_same_turn(self):
        action_id = uuid4()
        url = reverse("session-play", args=[self.session.pk])  # pyright: ignore

        payload = {
            "action_id": str(action_id),
            "message": "I inspect the room.",
        }

        first = self.client.post(url, payload, format="json")
        second = self.client.post(url, payload, format="json")

        self.assertEqual(first.status_code, 201)  # pyright: ignore
        self.assertEqual(second.status_code, 201)  # pyright: ignore
        self.assertEqual(first.data, second.data)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore

    def test_duplicate_play_rejects_different_message(self):
        action_id = uuid4()
        url = reverse("session-play", args=[self.session.pk])  # pyright: ignore

        first = self.client.post(
            url,
            {
                "action_id": str(action_id),
                "message": "I inspect the room.",
            },
            format="json",
        )

        with self.assertRaisesMessage(
            ValidationError,
            f"Existing turn with action_id {action_id} has a different original_message: I inspect the room. vs I attack the Garrick.",
        ):  # pyright: ignore
            self.client.post(
                url,
                {
                    "action_id": str(action_id),
                    "message": "I attack the Garrick.",
                },
                format="json",
            )

        self.assertEqual(first.status_code, 201)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore

    def test_narrate_verified_result(self):
        client = Mock()

        client.models.generate_content.return_value.text = (
            "Your sword stikes Garrick, but he remains standing."
        )

        provider = GeminiAIProvider(
            client=client,
            model="test-model",
        )

        context = {
            "location": {
                "slug": "lanterns_rest",
                "name": "Lantern's Rest",
            },
            "action": {
                "original_message": "I attack Garrick.",
                "mechanical_result": {
                    "type": "attack",
                    "target": "garrick_voss",
                    "target_remaining_hp": 13,
                    "target_alive": True,
                },
            },
        }

        narration = provider.narrate(context)

        self.assertIn("Garrick", narration)
        self.assertIn("standing", narration)


class AttackMechanicsTest(TestCase):
    @patch("game.mechanics.roll_d20", return_value=15)
    def test_successful_attack(self, mock_roll):
        result = resolve_attack(
            strength=14,
            weapon_damage=5,
            defense=12,
        )

        self.assertTrue(result.hit)
        self.assertEqual(result.total, 17)
        self.assertEqual(result.damage, 7)

    @patch("game.mechanics.roll_d20", return_value=1)
    def test_natural_one_always_miss(self, mock_roll):
        result = resolve_attack(
            strength=20,
            defense=5,
            weapon_damage=5,
        )

        self.assertFalse(result.hit)
        self.assertEqual(result.damage, 0)


class AttackActionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.other_user = User.objects.create_user(
            username="otherplayer",
            password="otherpassword",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.tavern = Location.objects.create(
            campaign=self.campaign,
            slug="tavern",
            name="The Tavern",
            data={
                "connections": ["square"],
            },
        )

        self.square = Location.objects.create(
            campaign=self.campaign,
            slug="square",
            name="Square",
            data={
                "connections": ["tavern"],
            },
        )

        self.npc = NPC.objects.create(
            campaign=self.campaign,
            slug="garrick",
            name="Garrick",
            starting_location=self.tavern,
            data={
                "initial_state": {
                    "hp": 18,
                    "max_hp": 18,
                    "alive": True,
                    "trust": 0,
                    "hostility": 0,
                },
            },
        )

        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
            inventory=["rusty_sword"],
        )

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def attack(self, *, action_id=None, target="garrick"):
        return self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id or uuid4()),
                "type": "attack",
                "target": target,
                "weapon": "rusty_sword",
            },
            format="json",
        )

    @patch("game.mechanics.roll_d20", return_value=15)
    def test_attack_creates_turn_and_deals_damage(self, mock_roll):
        response = self.attack()

        self.assertEqual(response.status_code, 201)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(npc_state.hp, 13)
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

    @patch("game.mechanics.roll_d20", return_value=15)
    def test_duplicate_action_does_not_deal_damage_twice(self, mock_roll):
        action_id = uuid4()

        first = self.attack(action_id=action_id)
        second = self.attack(action_id=action_id)

        self.assertEqual(first.status_code, 201)  # pyright: ignore
        self.assertEqual(second.status_code, 201)  # pyright: ignore
        self.assertEqual(first.data["id"], second.data["id"])  # pyright: ignore

        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        self.assertEqual(npc_state.hp, 13)
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore

    def test_cannot_attack_npc_in_another_location(self):
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        npc_state.current_location = self.square
        npc_state.save(update_fields=["current_location"])

        with self.assertRaisesMessage(ValidationError, "not in the same location"):  # pyright: ignore
            self.attack()

        self.session.refresh_from_db()  # pyright: ignore
        npc_state.refresh_from_db()

        self.assertEqual(self.session.turn_number, 0)  # pyright: ignore
        self.assertEqual(npc_state.hp, 18)
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 0)

    def test_cannot_attack_without_weapon(self):
        player = PlayerState.objects.get(session=self.session)
        player.inventory = []
        player.save(update_fields=["inventory"])

        with self.assertRaisesMessage(ValidationError, "does not have weapon"):  # pyright: ignore
            self.attack()

        self.session.refresh_from_db()  # pyright: ignore
        npc_state = NPCState.objects.get(session=self.session, npc=self.npc)

        self.assertEqual(self.session.turn_number, 0)  # pyright: ignore
        self.assertEqual(npc_state.hp, 18)
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 0)

    def test_cannot_attack_another_users_session(self):
        other_character = Character.objects.create(
            owner=self.other_user,
            name="Borin",
        )
        other_session = create_game_session(
            owner=self.other_user,  # pyright: ignore
            character=other_character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

        response = self.client.post(
            reverse("session-actions", args=[other_session.pk]),  # pyright: ignore
            {
                "action_id": str(uuid4()),
                "type": "attack",
                "target": "garrick",
                "weapon": "rusty_sword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=other_session).count(), 0)


class MovementActionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.tavern = Location.objects.create(
            campaign=self.campaign,
            slug="tavern",
            name="The Tavern",
            data={
                "connections": ["square"],
            },
        )

        self.square = Location.objects.create(
            campaign=self.campaign,
            slug="square",
            name="Square",
            data={
                "connections": ["tavern"],
            },
        )

        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
        )

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def test_move_creates_turn_and_updates_location(self):
        action_id = uuid4()

        response = self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id),
                "type": "move",
                "destination": "square",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.current_location, self.square)  #  pyright: ignore
        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

    def test_cannot_move_to_unconnected_location(self):
        action_id = uuid4()

        with self.assertRaisesMessage(ValidationError, "not connected"):  # pyright: ignore
            self.client.post(
                reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
                {
                    "action_id": str(action_id),
                    "type": "move",
                    "destination": "nonexistent_location",
                },
                format="json",
            )

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.current_location, self.tavern)  # pyright: ignore
        self.assertEqual(self.session.turn_number, 0)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 0)

    def test_duplicate_move_action_does_not_increment_turn(self):
        action_id = uuid4()

        self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id),
                "type": "move",
                "destination": "square",
            },
            format="json",
        )

        self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id),
                "type": "move",
                "destination": "square",
            },
            format="json",
        )

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.current_location, self.square)  # pyright: ignore
        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)


class InspectActionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.other_user = User.objects.create_user(
            username="otherplayer",
            password="otherpassword",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.tavern = Location.objects.create(
            campaign=self.campaign,
            slug="tavern",
            name="The Tavern",
            data={
                "connections": ["square"],
            },
        )

        self.square = Location.objects.create(
            campaign=self.campaign,
            slug="square",
            name="Square",
            data={
                "connections": ["tavern"],
            },
        )

        self.npc = NPC.objects.create(
            campaign=self.campaign,
            slug="garrick",
            name="Garrick",
            starting_location=self.tavern,
            data={
                "initial_state": {
                    "hp": 18,
                    "max_hp": 18,
                    "alive": True,
                    "trust": 0,
                    "hostility": 0,
                },
            },
        )

        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
            inventory=["rusty_sword"],
        )

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def inspect(self, action_id=None):
        return self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id or uuid4()),
                "type": "inspect",
            },
            format="json",
        )

    def test_inspect_returns_location(self):
        response = self.inspect()

        self.assertEqual(response.status_code, 201)  #  pyright: ignore

        result = response.data["mechanical_result"]  # pyright: ignore

        self.assertEqual(result["type"], "inspect")
        self.assertEqual(result["location"]["slug"], "tavern")

    def test_inspect_returns_visible_npcs(self):
        response = self.inspect()

        self.assertEqual(response.status_code, 201)  # pyright: ignore

        npcs = response.data["mechanical_result"]["npcs"]  # pyright: ignore

        self.assertEqual(len(npcs), 1)
        self.assertEqual(npcs[0]["slug"], "garrick")

    def test_inspect_creates_turn(self):
        response = self.inspect()

        self.assertEqual(response.status_code, 201)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore

        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

    def test_duplicate_inspect_action_does_not_increment_turn(self):
        action_id = uuid4()

        self.inspect(action_id=action_id)
        self.inspect(action_id=action_id)

        self.session.refresh_from_db()  # pyright: ignore

        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)


class TalkActionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.other_user = User.objects.create_user(
            username="otherplayer",
            password="otherpassword",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.tavern = Location.objects.create(
            campaign=self.campaign,
            slug="tavern",
            name="The Tavern",
            data={
                "connections": ["square"],
            },
        )

        self.square = Location.objects.create(
            campaign=self.campaign,
            slug="square",
            name="Square",
            data={
                "connections": ["tavern"],
            },
        )

        self.npc = NPC.objects.create(
            campaign=self.campaign,
            slug="garrick",
            name="Garrick",
            starting_location=self.tavern,
            data={
                "initial_state": {
                    "hp": 18,
                    "max_hp": 18,
                    "alive": True,
                    "trust": 0,
                    "hostility": 0,
                },
            },
        )

        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
            inventory=["rusty_sword"],
        )

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def talk(self, action_id=None, message="Hello!"):
        return self.client.post(
            reverse("session-actions", args=[self.session.pk]),  # pyright: ignore
            {
                "action_id": str(action_id or uuid4()),
                "type": "talk",
                "target": "garrick",
                "message": message,
            },
            format="json",
        )

    def test_talk_creates_turn_and_returns_response(self):
        response = self.talk(message="Hello!")

        self.assertEqual(response.status_code, 201)  # pyright: ignore

        self.session.refresh_from_db()  # pyright: ignore

        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

        result = response.data["mechanical_result"]  # pyright: ignore

        self.assertEqual(result["type"], "talk")
        self.assertIn("message", result)

    def test_duplicate_talk_action_does_not_increment_turn(self):
        action_id = uuid4()

        self.talk(action_id=action_id, message="Hello!")
        self.talk(action_id=action_id, message="Hello!")

        self.session.refresh_from_db()  # pyright: ignore

        self.assertEqual(self.session.turn_number, 1)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 1)

    def test_cannot_talk_to_npc_in_another_location(self):
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        npc_state.current_location = self.square
        npc_state.save(update_fields=["current_location"])

        with self.assertRaisesMessage(ValidationError, "not found in the session"):  # pyright: ignore
            self.talk(message="Hello!")

        self.session.refresh_from_db()  # pyright: ignore
        self.assertEqual(self.session.turn_number, 0)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 0)

    def test_cannot_talk_to_another_users_session(self):
        other_character = Character.objects.create(
            owner=self.other_user,
            name="Borin",
        )
        other_session = create_game_session(
            owner=self.other_user,  # pyright: ignore
            character=other_character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

        response = self.client.post(
            reverse("session-actions", args=[other_session.pk]),  # pyright: ignore
            {
                "action_id": str(uuid4()),
                "type": "talk",
                "target": "garrick",
                "message": "Hello!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=other_session).count(), 0)

    def test_talk_without_message_returns_error(self):
        response = self.talk(message="")

        self.assertEqual(response.status_code, 400)  # pyright: ignore
        self.assertEqual(GameTurn.objects.filter(session=self.session).count(), 0)


class NPCKnowledgeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testplayer",
            password="testpassword",
        )

        self.campaign = Campaign.objects.create(
            slug="test_campaign",
            title="Test Campaign",
            data={
                "starting_state": {
                    "location": "tavern",
                    "flags": {"quest_started": False},
                },
            },
        )

        self.location = Location.objects.create(
            campaign=self.campaign, slug="tavern", name="The Tavern"
        )

        self.npc = NPC.objects.create(
            campaign=self.campaign,
            slug="garrick",
            name="Garrick",
            starting_location=self.location,
            data={
                "initial_state": {
                    "hp": 18,
                    "max_hp": 18,
                    "alive": True,
                    "trust": 0,
                    "hostility": 0,
                },
            },
        )
        self.character = Character.objects.create(
            owner=self.user,
            name="Aric",
            hp=20,
            max_hp=20,
            gold=10,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.session = create_game_session(
            owner=self.user,  # pyright: ignore
            character=self.character,  # pyright: ignore
            campaign=self.campaign,  # pyright: ignore
        )

    def test_knowledge_unlock(self):
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        npc_state.npc.data["knowledge"] = [
            {
                "id": "public",
                "text": "The village is quiet.",
                "conditions": {"min_trust": 0},
            },
            {
                "id": "private",
                "text": "I know something important.",
                "conditions": {"min_trust": 5},
            },
        ]

        npc_state.npc.save(update_fields=["data"])

        npc_state.trust = 0
        npc_state.save(update_fields=["trust"])

        self.assertEqual(
            get_permitted_knowledge(npc_state.session, npc_state),
            ["The village is quiet."],
        )

        npc_state.trust = 5
        npc_state.save(update_fields=["trust"])

        self.assertEqual(
            get_permitted_knowledge(npc_state.session, npc_state),
            [
                "The village is quiet.",
                "I know something important.",
            ],
        )

    def test_attack_reduces_trust_and_increases_hostility(self):
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        npc_state.trust = 0
        npc_state.hostility = 0
        npc_state.save(update_fields=["trust", "hostility"])

        apply_relationship_event(npc_state=npc_state, event="attacked_npc")  # pyright: ignore
        npc_state.refresh_from_db()  # pyright: ignore

        self.assertEqual(npc_state.trust, -5)
        self.assertEqual(npc_state.hostility, 5)

    def test_relationship_values_are_clamped(self):
        npc_state = NPCState.objects.get(
            session=self.session,
            npc=self.npc,
        )

        npc_state.trust = -99
        npc_state.hostility = 99
        npc_state.save(update_fields=["trust", "hostility"])

        apply_relationship_event(npc_state=npc_state, event="attacked_npc")  # pyright: ignore
        npc_state.refresh_from_db()  # pyright: ignore

        self.assertEqual(npc_state.trust, -100)
        self.assertEqual(npc_state.hostility, 100)
