from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="allow")


class CampaignSchema(Schema):
    id: str
    title: str
    version: str = "1.0"
    description: str = ""
    starting_state: dict[str, Any]
    dm_secret: dict[str, Any] = Field(default_factory=dict)


class LocationSchema(Schema):
    id: str
    name: str
    type: str
    description: str = ""
    npcs: list[str] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)
    encounters: list[str] = Field(default_factory=list)


class NPCInitialStateSchema(Schema):
    hp: int = Field(gt=0)
    max_hp: int = Field(gt=0)
    defense: int = Field(gt=0)
    hostility: int = Field(ge=0)
    trust: int = 0
    alive: bool = True
    recruited: bool = False

    @model_validator(mode="after")
    def validate_hp(self):
        if self.hp > self.max_hp:
            raise ValueError("HP cannot be greater than max HP")
        return self


class SecretSchema(Schema):
    id: str
    description: str
    reveal_condition: dict[str, Any] = Field(default_factory=dict)


class NPCSchema(Schema):
    id: str
    name: str
    age: int | None = None
    species: str
    role: str
    location: str

    appearance: str
    background: str

    personality: dict[str, Any] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    public_knowledge: list[str] = Field(default_factory=list)

    secrets: list[SecretSchema]

    relationships: dict[str, str] = Field(default_factory=dict)
    initial_state: NPCInitialStateSchema

    dialogue_examples: dict[str, str] = Field(default_factory=dict)


class QuestSchema(Schema):
    id: str
    title: str
    description: str = ""
    objectives: list[dict[str, Any]] = Field(default_factory=list)


class ItemSchema(Schema):
    id: str
    name: str
    type: str
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class EnemiesSchema(Schema):
    id: str
    name: str
    hp: int
    defense: int
    attack_bonus: int
    damage_dice: str


class EncounterSchema(Schema):
    id: str
    name: str
    location: str
    enemies: list[EnemiesSchema] = Field(default_factory=list)


class EndingSchema(Schema):
    id: str
    title: str
    requirements: dict[str, Any] = Field(default_factory=dict)
    consequences: dict[str, Any] = Field(default_factory=dict)


class CampaignBundle(BaseModel):
    campaign: CampaignSchema
    locations: list[LocationSchema]
    npcs: list[NPCSchema]
    quests: list[QuestSchema]
    items: list[ItemSchema]
    encounters: list[EncounterSchema]
    endings: list[EndingSchema]

    @model_validator(mode="after")
    def validate_references(self):
        locations = {location.id for location in self.locations}
        npcs = {npc.id for npc in self.npcs}
        encounters = {encounter.id for encounter in self.encounters}

        for group in (
            self.locations,
            self.npcs,
            self.quests,
            self.items,
            self.encounters,
            self.endings,
        ):
            ids = [object.id for object in group]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate IDs found in {group.__class__.__name__}")

        start = self.campaign.starting_state["location"]
        if start not in locations:
            raise ValueError(f"Starting location '{start}' not found in locations")

        for location in self.locations:
            for target in location.connections:
                if target not in locations:
                    raise ValueError(
                        f"Location '{location.id}' has a connection to non-existent location '{target}'"
                    )
            for npc_id in location.npcs:
                if npc_id not in npcs:
                    raise ValueError(
                        f"Location '{location.id}' has a reference to non-existent NPC '{npc_id}'"
                    )
            for encounter_id in location.encounters:
                if encounter_id not in encounters:
                    raise ValueError(
                        f"Location '{location.id}' has a reference to non-existent Encounter '{encounter_id}'"
                    )
            for npc in self.npcs:
                if npc.location not in locations:
                    raise ValueError(
                        f"NPC '{npc.id}' has a reference to non-existent Location '{npc.location}'"
                    )
            for encounter in self.encounters:
                if encounter.location not in locations:
                    raise ValueError(
                        f"Encounter '{encounter.id}' has a reference to non-existent Location '{encounter.location}'"
                    )
        return self
