from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from pydantic import ValidationError

from world.importer import import_campaign, load_campaign


class Command(BaseCommand):
    help = "Validate and import a YAML campaing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--campaign",
            required=True,
            type=str,
        )

    def handle(self, *args, **options):
        campaign_id = options["campaign"]

        # setting.BASE_DIR points to banckend/
        project_root = Path(settings.BASE_DIR).parent

        directory = Path(project_root / "data" / "campaigns" / campaign_id)

        if not directory.is_dir():
            raise CommandError(f"Campaign directory {directory} does not exist")

        try:
            bundle = load_campaign(directory)
            campaign = import_campaign(bundle)  # pyright: ignore
        except (ValidationError, ValueError, KeyError, OSError) as exc:
            raise CommandError(
                f"Failed to import campaign {campaign_id}: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported campaign {campaign.title}")  # pyright: ignore
        )
