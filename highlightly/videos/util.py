from scrapers.models import ScheduledMatch


def create_video_metadata(scheduled_match: ScheduledMatch):
    """Create all metadata required for a YouTube video including a title, description, tags, and a thumbnail."""
    title = create_video_title(scheduled_match)
    description = create_video_description(scheduled_match)
    tags = create_video_tags(scheduled_match)

    thumbnail_filename = create_video_thumbnail(scheduled_match)

    pass

def create_video_title(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video title."""
    pass

def create_video_description(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video description."""
    pass

def create_video_tags(scheduled_match: ScheduledMatch) -> list[str]:
    """Use the teams, tournament, and, if necessary, extra match information to create tags for the video."""
    pass

def create_video_thumbnail(scheduled_match: ScheduledMatch) -> str:
    """
    Use the team logos, tournament logo, tournament context, and if necessary, extra match information to create a
    thumbnail for the video. The name of the created thumbnail file is returned.
    """
    pass
