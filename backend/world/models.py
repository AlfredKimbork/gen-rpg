from django.db import models


class Campaign(models.Model):
    objects = models.Manager()
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.title} (v{self.version})"


class Location(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_location_slug_per_campaign",
            ),
        )

    def __str__(self):
        return f"{self.name}"


class NPC(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="npcs",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    starting_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="starting_npcs",
    )
    data = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_campaign_npc",
            ),
        )

    def __str__(self):
        return f"{self.name}"


class Quest(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="quests",
    )
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_campaign_quest",
            ),
        )


class Item(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="items",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_campaign_item",
            ),
        )


class Encounter(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="encounters",
    )
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="encounters",
    )
    data = models.JSONField(default=dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_campaign_encounter",
            ),
        )


class Ending(models.Model):
    objects = models.Manager()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="endings",
    )
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_campaign_ending",
            ),
        )
