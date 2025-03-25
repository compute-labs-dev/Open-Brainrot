#!/usr/bin/env python3
"""
Test script to verify database interactions with the voice field.
This script tests the insertion of a video record with the voice field properly set.
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


def test_insert_video_with_voice():
    """Test inserting a video record with the voice field properly set."""
    print("\n=== Testing Video Insertion with Voice Field ===")

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
            "voice": test_voice,  # Explicitly set the voice field
            "s3_url": "",  # Empty placeholder
            "status": "processing",
            "background_video": "minecraft",
            "word_count": 100,
            "metadata": {
                "model": "o3mini",
                "start_time": datetime.now().isoformat(),
                "voice": test_voice,  # Also include in metadata for consistency
                "title": f"Test Video - {test_voice}",
                "description": "Test video for schema verification"
            }
        }

        print(f"📝 Attempting to insert video with voice: {test_voice}")
        print(f"📝 Video data: {json.dumps(video_data, indent=2)}")

        # Insert the video
        result = db.insert_video(video_data)

        if result and len(result) > 0:
            video_id = result[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id}")
            print(f"✅ Inserted data: {json.dumps(result[0], indent=2)}")

            # Verify the voice field was set correctly
            if result[0].get("voice") == test_voice:
                print(
                    f"✅ Voice field was set correctly to: {result[0].get('voice')}")
            else:
                print(
                    f"❌ Voice field was not set correctly. Expected: {test_voice}, Got: {result[0].get('voice')}")

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
            print(f"❌ Failed to insert video")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_insert_video_with_voice()
