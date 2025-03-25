#!/usr/bin/env python
"""
Test script to verify the fix for video/audio duration mismatch.
This will generate a video from test_input.txt and validate that 
the video duration matches the audio duration.
"""

import os
import logging
import time
from audio import audio_wrapper
from video_generator import get_duration, add_subtitles_and_overlay_audio
import subprocess
from math import ceil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_video_fix")


def get_audio_duration(audio_path):
    """Get the duration of an audio file in seconds"""
    try:
        import wave
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception:
        # Fallback method using ffprobe
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
            output = subprocess.check_output(cmd).decode('utf-8').strip()
            return float(output)
        except Exception:
            # If all else fails, return a default duration
            return 60.0  # Default to 1 minute


def format_time(seconds):
    """Format seconds to MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def main():
    # Create test directories if they don't exist
    os.makedirs('temp', exist_ok=True)
    os.makedirs('audio', exist_ok=True)
    os.makedirs('final', exist_ok=True)

    timestamp = int(time.time())
    test_dir = f'temp/test_{timestamp}'
    os.makedirs(test_dir, exist_ok=True)

    logger.info("Starting video/audio duration fix test")

    # Step 1: Read and save the input text
    with open("test_input.txt", "r") as f:
        input_text_content = f.read()

    # Save transcript to temp directory
    transcript_path = f"{test_dir}/transcript.txt"
    with open(transcript_path, "w") as f:
        f.write(input_text_content)
    logger.info(f"Saved transcript to: {transcript_path}")

    # Step 1: Generate audio from test_input.txt
    input_text = "test_input.txt"
    audio_output = f"{test_dir}/test_audio.wav"
    voice = "donald_trump"

    logger.info(f"Generating audio using voice: {voice}")
    audio_wrapper(input_text, audio_output, voice)

    # Step 2: Get audio duration
    audio_duration = get_audio_duration(audio_output)
    logger.info(
        f"Generated audio duration: {format_time(audio_duration)} ({audio_duration:.2f} seconds)")

    # Step 3: Create a short video file for testing
    video_path = "assets/minecraft.mp4"
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return

    video_duration = get_duration(video_path)
    logger.info(
        f"Original video duration: {format_time(video_duration)} ({video_duration:.2f} seconds)")

    # Step 4: Create a simple subtitle file
    subtitle_path = f"{test_dir}/test_subtitles.ass"
    with open(subtitle_path, 'w') as f:
        f.write('''[Script Info]
Title: Test Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,Testing video generation with long audio
Dialogue: 0,0:00:06.00,0:00:10.00,Default,,0,0,0,,This should extend the video to match audio length
''')

    # Step 5: Generate video with subtitles and audio
    output_video = f"{test_dir}/final_video.mp4"
    logger.info(f"Generating video with fixed code...")

    try:
        add_subtitles_and_overlay_audio(
            video_path, audio_output, subtitle_path, output_video)

        # Step 6: Verify durations match
        final_video_duration = get_duration(output_video)
        logger.info(
            f"Final video duration: {format_time(final_video_duration)} ({final_video_duration:.2f} seconds)")
        logger.info(
            f"Audio duration: {format_time(audio_duration)} ({audio_duration:.2f} seconds)")

        if abs(final_video_duration - audio_duration) <= 3:  # Allow 3 second margin
            logger.info("✅ SUCCESS: Video duration matches audio duration!")
            logger.info("The fix has been applied successfully.")
        else:
            logger.error(
                "❌ ERROR: Video duration still doesn't match audio duration.")
            logger.error(
                f"Video: {format_time(final_video_duration)} vs Audio: {format_time(audio_duration)}")
            logger.error("The fix might not be working as expected.")

        # Show file paths for manual verification
        logger.info(f"\nGenerated files:")
        logger.info(f"Transcript: {transcript_path}")
        logger.info(f"Audio: {audio_output}")
        logger.info(f"Video: {output_video}")
        logger.info(
            f"To manually verify, you can play these files with any media player.")

    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
