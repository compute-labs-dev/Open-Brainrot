#!/usr/bin/env python3
"""
Test script to verify that the insert_video method in db_client.py correctly handles the voice field.
This script directly tests the database client without running the full video generation process.
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
    """Test that the insert_video method correctly handles the voice field."""
    print("\n=== Testing insert_video Method with Voice Field ===")

    try:
        # Initialize the Supabase client
        db = SupabaseClient()
        print("✅ Supabase client initialized")

        # Create test data
        test_digest_id = str(uuid.uuid4())
        test_voice = "donald_trump"
        test_timestamp = int(datetime.now().timestamp())

        # Test case 1: Voice field explicitly set
        print("\n📝 Test Case 1: Voice field explicitly set")
        video_data_1 = {
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

        print(f"📝 Video data: {json.dumps(video_data_1, indent=2)}")
        result_1 = db.insert_video(video_data_1)

        if result_1 and len(result_1) > 0:
            video_id_1 = result_1[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id_1}")
            
            if result_1[0].get("voice") == test_voice:
                print(
                    f"✅ Voice field was set correctly to: {result_1[0].get('voice')}")
            else:
                print(
                    f"❌ Voice field was not set correctly. Expected: {test_voice}, Got: {result_1[0].get('voice')}")
            
            # Clean up
            delete_result = db.supabase.table(
                "videos").delete().eq("id", video_id_1).execute()
            if delete_result.data:
                print(f"✅ Test video deleted successfully")
        else:
            print(f"❌ Failed to insert video")

        # Test case 2: Voice field in metadata only
        print("\n📝 Test Case 2: Voice field in metadata only")
        video_data_2 = {
            "digest_id": test_digest_id,
            "s3_url": "",
            "status": "processing",
            "background_video": "minecraft",
            "word_count": 100,
            "metadata": {
                "model": "o3mini",
                "start_time": datetime.now().isoformat(),
                "voice": test_voice,
                "title": f"Test Video - {test_voice}",
                "description": "Test video for schema verification"
            }
        }

        print(f"📝 Video data: {json.dumps(video_data_2, indent=2)}")
        result_2 = db.insert_video(video_data_2)

        if result_2 and len(result_2) > 0:
            video_id_2 = result_2[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id_2}")
            
            if result_2[0].get("voice") == test_voice:
                print(
                    f"✅ Voice field was extracted from metadata and set correctly to: {result_2[0].get('voice')}")
            else:
                print(
                    f"❌ Voice field was not set correctly. Expected: {test_voice}, Got: {result_2[0].get('voice')}")
            
            # Clean up
            delete_result = db.supabase.table(
                "videos").delete().eq("id", video_id_2).execute()
            if delete_result.data:
                print(f"✅ Test video deleted successfully")
        else:
            print(f"❌ Failed to insert video")

        # Test case 3: Voice field as voice_type (legacy)
        print("\n📝 Test Case 3: Voice field as voice_type (legacy)")
        video_data_3 = {
            "digest_id": test_digest_id,
            "voice_type": test_voice,  # Using legacy field name
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

        print(f"📝 Video data: {json.dumps(video_data_3, indent=2)}")
        result_3 = db.insert_video(video_data_3)

        if result_3 and len(result_3) > 0:
            video_id_3 = result_3[0]["id"]
            print(f"✅ Video inserted successfully with ID: {video_id_3}")
            
            if result_3[0].get("voice") == test_voice:
                print(
                    f"✅ Voice field was converted from voice_type and set correctly to: {result_3[0].get('voice')}")
            else:
                print(
                    f"❌ Voice field was not set correctly. Expected: {test_voice}, Got: {result_3[0].get('voice')}")
            
            # Clean up
            delete_result = db.supabase.table(
                "videos").delete().eq("id", video_id_3).execute()
            if delete_result.data:
                print(f"✅ Test video deleted successfully")
        else:
            print(f"❌ Failed to insert video")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_insert_video_with_voice() 
