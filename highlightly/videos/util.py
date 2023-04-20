from scrapers.models import ScheduledMatch


def create_video_metadata(scheduled_match: ScheduledMatch):
    """Create all metadata required for a YouTube video including a title, description, tags, and a thumbnail."""
    title = create_video_title(scheduled_match)
    description = create_video_description(scheduled_match)
    tags = create_video_tags(scheduled_match)

    thumbnail_filename = create_video_thumbnail(scheduled_match)

    print(title, tags, thumbnail_filename)
    print(description)


def create_video_title(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video title."""
    # TODO: Generate an eye catching initial part of the video title based on the context of the match.
    team_part = f"{scheduled_match.team_1.name} vs {scheduled_match.team_2.name}"
    basic_title = f"{team_part} - HIGHLIGHTS | {scheduled_match.tournament.name}"

    return basic_title


# TODO: Maybe add the players from each team to the description when doing post game metadata.
# TODO: Maybe add the credits for where the vod is from.
def create_video_description(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video description."""
    tournament = scheduled_match.tournament
    game = scheduled_match.team_1.get_game_display()

    channel_part = f"Highlightly brings you accurate highlights quickly, condensing all the best {game} has to offer. " \
                   f"Catch the best moments from all your favorite {game} teams. Watch the best players in the world" \
                   f"compete at the highest levels of {game}.\n"

    match_part = f"Highlights from all maps between {scheduled_match.team_1.name} and {scheduled_match.team_2.name} " \
                 f"({scheduled_match.get_format_display()})\n" \
                 f"{scheduled_match.tournament_context.title()} of {tournament.prize_pool_us_dollars} prize pool " \
                 f"{game} tournament ({tournament.name})\n" \
                 f"Match: {scheduled_match.url}\n" \
                 f"Tournament: {tournament.url}\n"

    channels_part = "Highlightly channels:\n" \
                    "Counter-Strike: https://www.youtube.com/channel/UCaLgPz7aH58L4nDku2rYl1Q\n" \
                    "Valorant: https://www.youtube.com/channel/UCR40P8gajrDJcaP3Y5pQVxQ\n" \
                    "League of Legends: https://www.youtube.com/channel/UCH97dRgcN7vvhzpfAZRiUlg\n"

    tags_part = f"#{scheduled_match.team_1.name.lower()} #{scheduled_match.team_2.name.lower()} #{game.replace(' ', '').lower()}"

    return f"{channel_part}\n{match_part}\n{channels_part}\n{tags_part}"


def create_video_tags(scheduled_match: ScheduledMatch) -> list[str]:
    """Use the teams, tournament, and, if necessary, extra match information to create tags for the video."""
    return [scheduled_match.team_1.name, scheduled_match.team_2.name, scheduled_match.tournament.name,
            scheduled_match.team_1.get_game_display(),  scheduled_match.tournament.location,
            scheduled_match.team_1.nationality, scheduled_match.team_2.nationality, scheduled_match.tournament_context,
            scheduled_match.get_format_display()]


def create_video_thumbnail(scheduled_match: ScheduledMatch) -> str:
    """
    Use the team logos, tournament logo, tournament context, and if necessary, extra match information to create a
    thumbnail for the video. The name of the created thumbnail file is returned.
    """
    pass
