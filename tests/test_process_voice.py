#!/usr/bin/env python3
"""
Test script to verify that the process_voice function correctly sets the voice field.
This script mocks the necessary components to test the process_voice function.
"""

import os
import sys
import uuid
import json
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import our modules
try:
    from server import process_voice
    from db_client import SupabaseClient
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


def test_process_voice():
    """Test that the process_voice function correctly sets the voice field."""
    print("\n=== Testing process_voice Function ===")

    try:
        # Create test data
        test_digest_id = str(uuid.uuid4())
        test_voice = "donald_trump"
        test_model = "o3mini"
        test_video = "minecraft"
        test_word_count = 100
        test_title = "Test Title"
        test_description = "Test Description"
        test_request_id = "test-request-id"

        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock text file
            text_file_path = os.path.join(temp_dir, "test.txt")
            with open(text_file_path, "w") as f:
                f.write("This is a test text for voice processing.")

            # Set up environment variables for testing
            with patch.dict(os.environ, {"SUPABASE_ENABLED": "true"}):
                # Mock the SupabaseClient class
                with patch("server.SupabaseClient") as MockSupabaseClient:
                    mock_db = MagicMock()
                    mock_db.insert_video.return_value = [{
                        "id": str(uuid.uuid4()),
                        "digest_id": test_digest_id,
                        "voice": test_voice,
                        "status": "processing"
                    }]

                    # Mock the update_video_status method
                    mock_db.update_video_status.return_value = True

                    # Set the return value of the SupabaseClient constructor
                    MockSupabaseClient.return_value = mock_db

                    # Mock the subprocess.run function to avoid actually running ffmpeg
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value = MagicMock(returncode=0)

                        # Mock the os.path.exists function to pretend the video file exists
                        with patch("os.path.exists") as mock_exists:
                            mock_exists.return_value = True

                            # Call the process_voice function with our test data
                            print(
                                f"📝 Calling process_voice with voice: {test_voice}")
                            result = process_voice(
                                voice=test_voice,
                                text="This is a test text for voice processing.",
                                word_count=test_word_count,
                                digest_id=test_digest_id,
                                title=test_title,
                                description=test_description,
                                model=test_model,
                                video=test_video,
                                temp_path=temp_dir,
                                request_id=test_request_id
                            )

                            # Check if the function returned successfully
                            if result:
                                print(
                                    "✅ process_voice function completed successfully")

                                # Check if insert_video was called with the correct voice
                                calls = mock_db.insert_video.call_args_list
                                if calls:
                                    # First call, first argument
                                    video_data = calls[0][0][0]
                                    print(
                                        f"📝 Video data passed to insert_video: {json.dumps(video_data, indent=2)}")

                                    if "voice" in video_data and video_data["voice"] == test_voice:
                                        print(
                                            f"✅ Voice field was correctly set to: {video_data['voice']}")
                                    else:
                                        print(
                                            f"❌ Voice field was not set correctly. Expected: {test_voice}, Got: {video_data.get('voice', 'Not set')}")

                                    # Check if voice is also in metadata
                                    if "metadata" in video_data and isinstance(video_data["metadata"], dict) and "voice" in video_data["metadata"] and video_data["metadata"]["voice"] == test_voice:
                                        print(
                                            f"✅ Voice field in metadata was correctly set to: {video_data['metadata']['voice']}")
                                    else:
                                        print(
                                            f"❌ Voice field in metadata was not set correctly")
                                else:
                                    print("❌ insert_video was not called")
                            else:
                                print("❌ process_voice function failed")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_process_voice()
