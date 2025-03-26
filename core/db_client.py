import os
from supabase import create_client, Client
from datetime import datetime
import json


class SupabaseClient:
    def __init__(self):
        url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError("Supabase URL and key must be provided")

        self.supabase: Client = create_client(url, key)

    def get_latest_digest(self):
        """Fetch the latest digest"""
        response = self.supabase.table("digests") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]
        return None

    def insert_video(self, video_data):
        """Insert a new video record"""
        try:
            # Ensure JSON serialization for metadata
            if "metadata" in video_data and isinstance(video_data["metadata"], dict):
                video_data["metadata"] = json.dumps(video_data["metadata"])

            # Ensure s3_url has a default value to avoid NOT NULL constraint violations
            if "s3_url" not in video_data:
                video_data["s3_url"] = ""  # Empty string as placeholder

            # Ensure voice field is set (renamed from voice_type if needed)
            if "voice_type" in video_data and "voice" not in video_data:
                video_data["voice"] = video_data.pop("voice_type")

            # Make sure voice field is not null
            if "voice" not in video_data or video_data["voice"] is None:
                print(
                    f"WARNING: voice field is missing or null in video_data: {video_data}")
                # Try to extract from metadata if available
                if "metadata" in video_data and isinstance(video_data["metadata"], str):
                    try:
                        metadata = json.loads(video_data["metadata"])
                        if "voice" in metadata and metadata["voice"]:
                            video_data["voice"] = metadata["voice"]
                            print(
                                f"Extracted voice from metadata: {video_data['voice']}")
                    except:
                        pass

            # Print video data for debugging
            print(
                f"Attempting to insert video data: {json.dumps({k: str(v)[:30] + '...' if isinstance(v, str) and len(v) > 30 else v for k, v in video_data.items()})}")

            response = self.supabase.table("videos") \
                .insert(video_data) \
                .execute()

            # Add debug logging
            print(f"Supabase insert response: {response}")

            # Make sure it's returning data in the expected format
            return response.data
        except Exception as e:
            # Improve error reporting
            print(f"Supabase insert error: {type(e).__name__}: {str(e)}")
            print(f"Video data keys: {list(video_data.keys())}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Error response: {e.response.text}")
            raise  # Re-raise to be caught by the caller

    def update_video_status(self, video_id, status, metadata=None):
        """Update video processing status"""
        update_data = {"status": status}

        # Extract s3_url from metadata if present
        if metadata and "s3_url" in metadata:
            update_data["s3_url"] = metadata.pop("s3_url")

        if metadata:
            update_data["metadata"] = json.dumps(metadata)

        response = self.supabase.table("videos") \
            .update(update_data) \
            .eq("id", video_id) \
            .execute()

        return response.data

    def get_pending_videos(self):
        """Get videos with 'processing' status"""
        response = self.supabase.table("videos") \
            .select("*") \
            .eq("status", "processing") \
            .execute()

        return response.data

    def get_digests_without_videos(self, limit=10):
        """Get digests that don't have associated videos yet"""
        # This is a more complex query that might need to be customized based on your schema
        response = self.supabase.table("digests") \
            .select("*") \
            .not_("id", "in",
                  self.supabase.from_("videos").select("digest_id")) \
            .limit(limit) \
            .execute()

        return response.data
