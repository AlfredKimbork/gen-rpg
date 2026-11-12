from pathlib import Path

import yaml
from django.db import transaction

from .models import NPC, Campaign, Encounter, Ending, Item, Location, Quest
from .schemas import CampaignBundle

FILES = (
    "campaign",
    "locations",
    "npcs",
    "quests",
    "items",
    "encounters",
    "endings",
)


def load_campaign(directory: Path) -> CampaignBundle:
    raw = {}

    for name in FILES:
        path = directory / f"{name}.yaml"

        with path.open("r", encoding="utf-8") as file:
            content = yaml.safe_load(file)

            if name == "campaign":
                raw[name] = content
            else:
                raw[name] = content[name]

    return CampaignBundle.model_validate(raw)


@transaction.atomic
def import_campaign(bundle: CampaignBundle) -> Campaign:
    definition = bundle.campaign

    campaign, _ = Campaign.objects.update_or_create(
        slug=definition.id,
        defaults={
            "title": definition.title,
            "version": definition.version,
            "description": definition.description,
            "data": definition.model_dump(mode="json"),
        },
    )

    locations = {}

    for definition in bundle.locations:
        location, _ = Location.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "name": definition.name,
                "description": definition.description,
                "data": definition.model_dump(mode="json"),
            },
        )
        locations[definition.id] = location

    for definition in bundle.npcs:
        NPC.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "name": definition.name,
                "starting_location": locations[definition.location],
                "data": definition.model_dump(mode="json"),
            },
        )

    for definition in bundle.quests:
        Quest.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "title": definition.title,
                "description": definition.description,
                "data": definition.model_dump(mode="json"),
            },
        )

    for definition in bundle.items:
        Item.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "name": definition.name,
                "data": definition.model_dump(mode="json"),
            },
        )

    for definition in bundle.encounters:
        Encounter.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "name": definition.name,
                "location": locations[definition.location],
                "data": definition.model_dump(mode="json"),
            },
        )

    for definition in bundle.endings:
        Ending.objects.update_or_create(
            campaign=campaign,
            slug=definition.id,
            defaults={
                "title": definition.title,
                "data": definition.model_dump(mode="json"),
            },
        )

    return campaign
