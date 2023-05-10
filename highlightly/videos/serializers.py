from rest_framework import serializers

from util.file_util import get_base64
from videos.models import VideoMetadata


class VideoMetadataSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = VideoMetadata
        fields = ["id", "match", "title", "description", "tags", "thumbnail", "language", "category_id"]

    @staticmethod
    def get_thumbnail(video_metadata: VideoMetadata) -> str:
        return get_base64(f"{video_metadata.match.create_unique_folder_path()}/{video_metadata.thumbnail_filename}")


class VideoMetadataUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoMetadata
        fields = ["title", "description", "tags", "language", "category_id"]

    def to_representation(self, video_metadata: VideoMetadata) -> dict:
        return VideoMetadataSerializer(video_metadata).data
