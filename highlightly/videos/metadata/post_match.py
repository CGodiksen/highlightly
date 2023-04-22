from scrapers.models import ScheduledMatch


def add_post_match_video_metadata(scheduled_match: ScheduledMatch):
    """
    Add metadata to the video metadata that can only be extracted once the match is finished. This includes
    statistics about the performance of each player during the match, the tournament context, and a frame
    from the match for the thumbnail.
    """
    pass
