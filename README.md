# Gen RPG

A single-player, D&D-inspired role-playing game powered by an AI Dungeon Master.

Players create characters, explore a persistent fantasy world, interact with NPCs, make decisions, fight enemies, and shape the story through natural-language actions.

Unlike traditional text adventures, the player is not restricted to predefined dialogue choices or actions.

The AI acts as the Dungeon Master, while the backend controls game mechanics, validates outcomes, and maintains persistent world state.

## Tech stack

| Component         | Technology                    |
| ----------------- | ----------------------------- |
| Frontend          | React, TypeScript, Vite       |
| Backend           | Django, Django REST Framework |
| Database          | PostgreSQL                    |
| AI                | Google Gemini API             |
| Python management | uv                            |
| Campaign content  | YAML                          |
| API validation    | DRF serializers and Pydantic  |
| Testing           | pytest, pytest-django         |

## Core principles

### 1. The backend is authoritative

The AI does not directly modify the database.

The backend manages:

- Character attributes and health
- Inventory and equipment
- Dice rolls and skill checks
- Combat calculations
- Quest progression
- NPC states and relationships
- World events
- Game saves

The AI interprets player intentions, generates dialogue, describes environments, and narrates verified outcomes.

### 2. Player freedom

Players should be able to attempt almost any reasonable action.

Actions are interpreted in the context of the current world, available resources, character abilities, and established game rules.

Not every action requires a dice roll.

### 3. Persistent consequences

Actions have lasting effects.

If an NPC dies, they remain dead. If the player steals an item, its ownership changes. If a quest is completed, the world remembers.

### 4. Consistent world lore

Campaigns are defined using YAML files.

These contain canonical locations, characters, items, quests, encounters, secrets, and possible endings.

The AI may improvise within the established world, but must not contradict canonical facts or previously verified events.

## Project structure

- `backend/characters/` — Player characters, attributes, equipment, inventory, and progression.
- `backend/world/` — Campaigns, NPCs, locations, quests, and persistent world state.
- `backend/game/` — Game sessions, dice, combat, action processing, and turn history.
- `backend/narrator/` — AI providers, prompts, context building, and narration.
- `frontend/` — React user interface.
- `data/campaigns/` — YAML campaign definitions.
- `docs/` — Architecture, game design, AI behavior, and development documentation.

## Development setup

### Requirements

- Python 3.12 or newer
- uv
- Node.js and npm
- PostgreSQL
- A Gemini API key

### Backend setup

From the project root:

```bash
cd backend
uv sync
```

Create a `.env` file:

```env
DEBUG=True
SECRET_KEY=replace-with-a-development-secret
DATABASE_URL=postgresql://rpg:rpg@localhost:5432/ai_dungeon
GEMINI_API_KEY=your-api-key
AI_MODEL=gemini-2.5-flash
```

The PostgreSQL database and user must exist before running migrations.

Run migrations:

```bash
uv run python manage.py migrate
```

Start Django:

```bash
uv run python manage.py runserver
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs separately from the Django API.

### Python dependencies

All Python dependencies must be managed using uv.

Examples:

```bash
uv add django
uv add djangorestframework
uv add google-genai
uv add pydantic
uv add pyyaml
uv add "psycopg[binary]"
uv add --dev pytest pytest-django
```

Do not use pip, Poetry, or Pipenv for this project.

## Campaign data

Campaigns are stored under:

`data/campaigns/<campaign_id>/`

The first campaign is **The Hollow Vale**.

Its files are:

- `campaign.yaml` — Main story, background, rules, and campaign metadata.
- `locations.yaml` — Locations, descriptions, connections, and discoveries.
- `npcs.yaml` — NPC personalities, relationships, goals, knowledge, and secrets.
- `quests.yaml` — Quest objectives, progression, and outcomes.
- `items.yaml` — Items, equipment, and usable objects.
- `encounters.yaml` — Enemies, combat encounters, and alternative resolutions.
- `endings.yaml` — Possible campaign conclusions.

Campaign YAML is immutable source content during gameplay.

Player-specific changes are saved to PostgreSQL.

## Loading campaign data

The planned Django management command is:

```bash
uv run python manage.py seed_world --campaign hollow_vale
```

**This command must be implemented before it can be used.**

The importer should validate YAML, resolve references between files, and create or update campaign definitions without resetting existing player saves.

## Gameplay loop

1. The player submits an action.
2. Django loads the current game state.
3. The AI interprets the action.
4. Django determines and resolves any required mechanics.
5. The AI narrates the verified outcome.
6. Django validates proposed state changes.
7. The game state and turn history are saved.
8. The frontend displays the result.

For simple actions, some stages can be combined.

## Planned API endpoints

| Method | Endpoint                      | Description           |
| ------ | ----------------------------- | --------------------- |
| POST   | `/api/characters/`            | Create a character    |
| GET    | `/api/characters/{id}/`       | Retrieve a character  |
| GET    | `/api/campaigns/`             | List campaigns        |
| POST   | `/api/sessions/`              | Start a game          |
| GET    | `/api/sessions/{id}/`         | Load a game           |
| GET    | `/api/sessions/{id}/turns/`   | Retrieve turn history |
| POST   | `/api/sessions/{id}/actions/` | Submit an action      |

These endpoints are planned and are not automatically created by this README.

## MVP scope

The initial prototype should support:

- Character creation
- One playable campaign
- AI-generated narration
- NPC dialogue
- D20 skill checks
- Basic combat
- Inventory
- Persistent world state
- Quest progression
- Save and load
- Multiple possible endings

## Testing

Run backend tests using:

```bash
uv run pytest
```

AI calls should be mocked in automated tests to avoid unnecessary API usage and ensure reproducible results.

Important test cases include:

- The AI cannot invent inventory items.
- Dead NPCs cannot speak or act.
- Hidden information is not revealed without justification.
- Combat damage is calculated by Python.
- A failed skill check cannot be narrated as a success.
- Player decisions persist after restarting the application.
- Invalid AI responses do not corrupt game state.
- One player's sessions cannot be accessed by another user.

## Development milestones

### Milestone 1 — Foundation

Django, PostgreSQL, React, API connectivity, and basic models.

### Milestone 2 — AI integration

Gemini integration, action interpretation, narration, and turn persistence.

### Milestone 3 — RPG mechanics

Characters, attributes, dice rolls, inventory, and combat.

### Milestone 4 — Campaign content

YAML importing, locations, NPCs, quests, and world memory.

### Milestone 5 — Playable prototype

Complete The Hollow Vale, test branching decisions, and improve reliability.

## Current status

Project architecture and starter campaign content defined.

Implementation is in progress.

## License

To be determined.
