from scrapers.models import Match
from videos.models import VideoMetadata


def add_post_match_video_metadata(match: Match):
    """
    Add metadata to the video metadata that can only be extracted once the match is finished. This includes
    statistics about the performance of each player during the match, the tournament context, the tournament logo,
    and a frame from the match for the thumbnail.
    """
    video_metadata = VideoMetadata.objects.get(match=match)
    new_tags = video_metadata.tags

    # Add the tournament context to the description and tags.
    video_metadata.description = video_metadata.description.replace("TOURNAMENT_CONTEXT", match.tournament_context)
    new_tags.append(match.tournament_context)
    video_metadata.tags = new_tags

    # TODO: Add players to description and tags.
    # TODO: Add credit to where the VOD is from to the description.
    # TODO: Add a frame from the match and the tournament logo to the thumbnail.
    # TODO: Create an image with tables for the match statistics and the MVP of the match with player specific statistics.

    video_metadata.save()
