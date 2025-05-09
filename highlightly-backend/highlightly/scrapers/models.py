import json
from pathlib import Path

import pytz
from colorfield.fields import ColorField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Game(models.TextChoices):
    COUNTER_STRIKE = "COUNTER_STRIKE", "Counter-Strike"
    LEAGUE_OF_LEGENDS = "LEAGUE_OF_LEGENDS", "League of Legends"
    VALORANT = "VALORANT", "Valorant"


class Tournament(models.Model):
    class Type(models.TextChoices):
        OFFLINE = "OFFLINE", "Offline"
        ONLINE = "ONLINE", "Online"

    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128, blank=True, null=True)
    short_name = models.CharField(max_length=32, blank=True, null=True)

    url = models.URLField(max_length=128, blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    prize_pool_us_dollars = models.CharField(max_length=32, blank=True, null=True)
    first_place_prize_us_dollars = models.CharField(max_length=32, blank=True, null=True)

    location = models.CharField(max_length=128, blank=True, null=True)
    tier = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    type = models.CharField(max_length=16, choices=Type.choices, blank=True, null=True)
    logo_filename = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.get_game_display()})"

    def get_display_name(self) -> str:
        return self.name if self.display_name is None else self.display_name


class Organization(models.Model):
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128, blank=True, null=True)
    # TODO: Maybe use a JSONField instead.
    alternate_names = models.CharField(max_length=256, blank=True, null=True)
    logo_filename = models.CharField(max_length=256, blank=True, null=True)
    background_color = ColorField(blank=True, null=True)

    def __str__(self) -> str:
        return self.name if self.display_name is None else self.display_name

    def get_names(self) -> list[str]:
        """Return all names that this organization is referred to as."""
        names = json.loads(self.alternate_names) if self.alternate_names is not None else []
        names.append(self.name)

        if self.display_name is not None:
            names.append(self.display_name)

        return names


class Team(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")

    game = models.CharField(max_length=32, choices=Game.choices)
    nationality = models.CharField(max_length=256, blank=True, null=True)
    ranking = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)
    url = models.URLField(max_length=128, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.organization} ({self.get_game_display()})"


# TODO: Handle when a profile picture cannot be found for a player.
class Player(models.Model):
    name = models.CharField(max_length=128)
    tag = models.CharField(max_length=128)
    nationality = models.CharField(max_length=128)
    profile_picture_filename = models.CharField(max_length=256, blank=True, null=True)

    url = models.URLField(max_length=128)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")

    def __str__(self) -> str:
        split_name = self.name.split(" ")
        return f"{split_name[0]} '{self.tag}' {' '.join(split_name[1:])}"


# TODO: When a match is created a websocket message should be sent.
class Match(models.Model):
    class Meta:
        verbose_name_plural = "matches"

    class Format(models.TextChoices):
        BEST_OF_1 = "BEST_OF_1", "Bo1"
        BEST_OF_3 = "BEST_OF_3", "Bo3"
        BEST_OF_5 = "BEST_OF_5", "Bo5"

    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_1_matches")
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_2_matches")

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    tournament_context = models.CharField(max_length=64, blank=True, null=True)
    format = models.CharField(max_length=16, choices=Format.choices)
    tier = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    url = models.URLField(max_length=128)

    created_at = models.DateTimeField(auto_now_add=True)
    start_datetime = models.DateTimeField()
    estimated_end_datetime = models.DateTimeField()

    create_video = models.BooleanField()
    finished = models.BooleanField(default=False)

    stream_url = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.team_1} VS. {self.team_2}"

    def create_unique_folder_path(self, folder: str | None = None) -> str:
        """Return a path that can be used to uniquely identify files related to this match."""
        team_1_name = self.team_1.organization.name.replace(" ", "-").replace("'", "").lower()
        team_2_name = self.team_2.organization.name.replace(" ", "-").replace("'", "").lower()

        match_part = f"{team_1_name}-vs-{team_2_name}"
        date_part = self.start_datetime.astimezone(pytz.timezone("Europe/Copenhagen")).strftime("%Y-%m-%d")
        path = f"media/matches/{self.tournament.name.replace(' ', '-').lower()}/{match_part}_{date_part}"

        full_path = f"{path}/{folder}" if folder is not None else path
        Path(full_path).mkdir(parents=True, exist_ok=True)

        return full_path


class GameVod(models.Model):
    class Host(models.TextChoices):
        YOUTUBE = "YOUTUBE", "YouTube"
        TWITCH = "TWITCH", "Twitch"

    match = models.ForeignKey(Match, on_delete=models.CASCADE)

    game_count = models.IntegerField(validators=[MinValueValidator(1)])
    map = models.CharField(max_length=64, blank=True, null=True)

    url = models.URLField(max_length=128, blank=True, null=True)
    host = models.CharField(max_length=16, choices=Host.choices)
    language = models.CharField(max_length=64)

    filename = models.CharField(max_length=256, blank=True, null=True)
    team_1_statistics_filename = models.CharField(max_length=128, blank=True, null=True)
    team_1_round_count = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    team_2_statistics_filename = models.CharField(max_length=128, blank=True, null=True)
    team_2_round_count = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)

    mvp = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True)
    game_start_offset = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)

    start_datetime = models.DateTimeField(blank=True, null=True)
    finished = models.BooleanField(default=False)
    highlighted = models.BooleanField(default=False)

    # Used to control the process to download the livestream of the VOD.
    process_id = models.IntegerField(blank=True, null=True)

    def __str__(self) -> str:
        return f"Map {self.game_count} VOD of {self.match}"


class GOTVDemo(models.Model):
    game_vod = models.OneToOneField(GameVod, on_delete=models.CASCADE)
    filename = models.CharField(max_length=256)

    def __str__(self) -> str:
        return f"Map {self.game_vod.game_count} GOTV demo of {self.game_vod.match}"
