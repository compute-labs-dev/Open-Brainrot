#!/usr/bin/env python3
"""
Test script to verify that the update_video_status method correctly handles the voice field.
This script tests updating a video record with metadata containing the voice field.
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


def test_update_video_status():
    """Test that the update_video_status method correctly handles the voice field."""
    print("\n=== Testing update_video_status Method with Voice Field ===")

    try:
        # Initialize the Supabase client
        db = SupabaseClient()
        print("✅ Supabase client initialized")

        # Create test data
        test_digest_id = str(uuid.uuid4())
        test_voice = "donald_trump"
        test_timestamp = int(datetime.now().timestamp())

        # First, insert a video record
        print("\n📝 Inserting test video record")
        video_data = {
            "digest_id": test_digest_id,
            "voice": test_voice,
            "s3_url": "",
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

        result = db.insert_video(video_data)

        if result and len(result) > 0:
            video_id = result[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id}")

            # Test case 1: Update with voice in metadata
            print("\n📝 Test Case 1: Update with voice in metadata")
            metadata = {
                "model": "o3mini",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "voice": test_voice,
                "duration_seconds": 60,
                "title": f"Updated Test Video - {test_voice}",
                "description": "Updated test video for schema verification"
            }

            update_result = db.update_video_status(
                video_id, "completed", metadata)
            print(f"✅ Video status updated: {update_result}")

            # Verify the update
            get_result = db.supabase.table("videos").select(
                "*").eq("id", video_id).execute()
            if get_result.data and len(get_result.data) > 0:
                updated_record = get_result.data[0]
                print(
                    f"✅ Retrieved updated record: {json.dumps(updated_record, indent=2)}")

                if updated_record.get("status") == "completed":
                    print(
                        f"✅ Status was updated correctly to: {updated_record.get('status')}")
                else:
                    print(
                        f"❌ Status was not updated correctly. Expected: completed, Got: {updated_record.get('status')}")

                # Check if metadata contains voice
                try:
                    updated_metadata = json.loads(
                        updated_record.get("metadata", "{}"))
                    if updated_metadata.get("voice") == test_voice:
                        print(
                            f"✅ Voice field in metadata was preserved: {updated_metadata.get('voice')}")
                    else:
                        print(
                            f"❌ Voice field in metadata was not preserved. Expected: {test_voice}, Got: {updated_metadata.get('voice')}")
                except json.JSONDecodeError:
                    print(
                        f"❌ Could not parse metadata JSON: {updated_record.get('metadata')}")
            else:
                print(f"❌ Could not retrieve updated record")

            # Test case 2: Update with s3_url in metadata
            print("\n📝 Test Case 2: Update with s3_url in metadata")
            test_s3_url = f"https://example.com/{test_digest_id}.mp4"
            metadata = {
                "model": "o3mini",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "voice": test_voice,
                "duration_seconds": 60,
                "s3_url": test_s3_url,
                "title": f"Updated Test Video with S3 URL - {test_voice}",
                "description": "Updated test video with S3 URL for schema verification"
            }

            update_result = db.update_video_status(
                video_id, "completed", metadata)
            print(f"✅ Video status updated with S3 URL: {update_result}")

            # Verify the update
            get_result = db.supabase.table("videos").select(
                "*").eq("id", video_id).execute()
            if get_result.data and len(get_result.data) > 0:
                updated_record = get_result.data[0]
                print(
                    f"✅ Retrieved updated record: {json.dumps(updated_record, indent=2)}")

                if updated_record.get("s3_url") == test_s3_url:
                    print(
                        f"✅ S3 URL was extracted from metadata and set correctly: {updated_record.get('s3_url')}")
                else:
                    print(
                        f"❌ S3 URL was not set correctly. Expected: {test_s3_url}, Got: {updated_record.get('s3_url')}")
            else:
                print(f"❌ Could not retrieve updated record")

            # Clean up
            delete_result = db.supabase.table(
                "videos").delete().eq("id", video_id).execute()
            if delete_result.data:
                print(f"\n✅ Test video deleted successfully")
            else:
                print(f"\n❌ Failed to delete test video")
        else:
            print(f"❌ Failed to insert video")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_update_video_status()
