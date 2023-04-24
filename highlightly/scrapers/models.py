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


class Team(models.Model):
    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)

    logo_filename = models.CharField(max_length=256, blank=True, null=True)
    background_color = ColorField(blank=True, null=True)

    nationality = models.CharField(max_length=256, blank=True, null=True)
    ranking = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)
    url = models.URLField(max_length=128, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.get_game_display()})"


# TODO: When a match is created a websocket message should be sent.
class Match(models.Model):
    class Meta:
        verbose_name_plural = "matches"

    class Format(models.TextChoices):
        BEST_OF_1 = "BEST_OF_1", "Bo1"
        BEST_OF_3 = "BEST_OF_3", "Bo3"
        BEST_OF_5 = "BEST_OF_5", "Bo5"

    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_1_matches")
    team_1_statistics_filename = models.CharField(max_length=128, blank=True, null=True)

    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_2_matches")
    team_2_statistics_filename = models.CharField(max_length=128, blank=True, null=True)

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

    def __str__(self) -> str:
        return f"{self.team_1} VS. {self.team_2}"

    def create_unique_folder_path(self) -> str:
        """Return a path that can be used to uniquely identify files related to this match."""
        match_part = f"{self.team_1.name.replace(' ', '_').lower()}_vs_{self.team_2.name.replace(' ', '_').lower()}"
        return f"{self.tournament.name.replace(' ', '_').lower()}/{match_part}_{self.id}"


# TODO: When the game vod is deleted, also delete the file.
class GameVod(models.Model):
    class Host(models.TextChoices):
        YOUTUBE = "YOUTUBE", "YouTube"
        TWITCH = "TWITCH", "Twitch"

    match = models.ForeignKey(Match, on_delete=models.CASCADE)

    game_count = models.IntegerField(validators=[MinValueValidator(1)])
    map = models.CharField(max_length=64)

    url = models.URLField(max_length=128)
    host = models.CharField(max_length=16, choices=Host.choices)
    language = models.CharField(max_length=64)
    filename = models.CharField(max_length=256)

    team_1_statistics_filename = models.CharField(max_length=128, blank=True, null=True)
    team_2_statistics_filename = models.CharField(max_length=128, blank=True, null=True)


# TODO: When the GOTV demo is deleted, also delete the file.
class GOTVDemo(models.Model):
    game_vod = models.OneToOneField(GameVod, on_delete=models.CASCADE)
    filename = models.CharField(max_length=256)
