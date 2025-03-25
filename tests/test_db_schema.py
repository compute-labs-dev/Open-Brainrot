#!/usr/bin/env python3
"""
Test script to verify database schema changes.
This script tests the interaction with the videos table using the updated schema.
"""

import os
import sys
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import our modules
try:
    from db_client import SupabaseClient
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


def test_insert_video():
    """Test inserting a video record with the updated schema."""
    print("\n=== Testing Video Insertion ===")

    try:
        # Initialize the Supabase client
        db = SupabaseClient()
        print("✅ Supabase client initialized")

        # Create test data
        test_digest_id = str(uuid.uuid4())
        test_voice = "donald_trump"
        test_timestamp = int(datetime.now().timestamp())

        # Create video data
        video_data = {
            "digest_id": test_digest_id,
            "voice": test_voice,
            "s3_url": "",  # Empty placeholder
            "status": "processing",
            "background_video": "minecraft",
            "word_count": 100,
            "metadata": {
                "model": "o3mini",
                "start_time": datetime.now().isoformat(),
                "title": f"Test Video - {test_voice}",
                "description": "Test video for schema verification"
            }
        }

        print(f"📝 Attempting to insert video with digest_id: {test_digest_id}")

        # Insert the video
        result = db.insert_video(video_data)

        if result and len(result) > 0:
            video_id = result[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id}")

            # Test updating the video status
            print(f"📝 Updating video status to 'completed'")
            update_result = db.update_video_status(video_id, "completed", {
                "end_time": datetime.now().isoformat(),
                "duration_seconds": 10.5
            })

            if update_result:
                print(f"✅ Video status updated successfully")

                # Test updating the s3_url
                s3_url = f"https://example.com/videos/{video_id}.mp4"
                print(f"📝 Updating video s3_url to: {s3_url}")

                update_s3_result = db.supabase.table("videos") \
                    .update({"s3_url": s3_url}) \
                    .eq("id", video_id) \
                    .execute()

                if update_s3_result.data:
                    print(f"✅ Video s3_url updated successfully")
                else:
                    print(f"❌ Failed to update video s3_url")

                # Clean up - delete the test video
                print(f"🧹 Cleaning up - deleting test video")
                delete_result = db.supabase.table("videos") \
                    .delete() \
                    .eq("id", video_id) \
                    .execute()

                if delete_result.data:
                    print(f"✅ Test video deleted successfully")
                else:
                    print(f"❌ Failed to delete test video")
            else:
                print(f"❌ Failed to update video status")
        else:
            print(f"❌ Failed to insert video")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_insert_video()
