from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    character_class: str = "Fighter"

    strength: int = Field(default=10, ge=1, le=20)
    dexterity: int = Field(default=10, ge=1, le=20)
    constitution: int = Field(default=10, ge=1, le=20)
    intelligence: int = Field(default=10, ge=1, le=20)
    wisdom: int = Field(default=10, ge=1, le=20)
    charisma: int = Field(default=10, ge=1, le=20)

    @model_validator(mode="after")
    def model_validator(self):
        attributes = (
            self.strength,
            self.dexterity,
            self.constitution,
            self.intelligence,
            self.wisdom,
            self.charisma,
        )

        if sum(attributes) > 75:
            raise ValueError("Total attribute points cannot exceed 75")

        return self
