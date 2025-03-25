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

    # Read transcript and split into lines
    with open(transcript_path, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Calculate timing for each line
    total_lines = len(lines)
    time_per_line = audio_duration / total_lines

    # Write subtitles in ASS format
    with open(subtitle_path, "w", encoding='utf-8') as f:
        # Write header
        f.write('[Script Info]\n')
        f.write('Title: Generated Subtitles\n')
        f.write('ScriptType: v4.00+\n')
        f.write('WrapStyle: 0\n')
        f.write('ScaledBorderAndShadow: yes\n')
        f.write('YCbCr Matrix: None\n')
        f.write('PlayResX: 404\n')
        f.write('PlayResY: 720\n\n')

        # Write styles
        f.write('[V4+ Styles]\n')
        f.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
        f.write('Style: Default,Arial,48,&HFFFFFF,&H000000,&H000000,&H000000,1,0,0,0,100,100,0,0,1,2,2,2,20,20,20,1\n\n')

        # Write events
        f.write('[Events]\n')
        f.write(
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

        # Write dialogue lines
        for i, line in enumerate(lines, 1):
            start_time = (i - 1) * time_per_line
            end_time = i * time_per_line

            # Format times as H:MM:SS.cc for ASS format
            start_str = f"{int(start_time//3600)}:{int((start_time % 3600)//60):02d}:{int(start_time % 60):02d}.{int((start_time % 1)*100):02d}"
            end_str = f"{int(end_time//3600)}:{int((end_time % 3600)//60):02d}:{int(end_time % 60):02d}.{int((end_time % 1)*100):02d}"

            # Write dialogue line in ASS format
            f.write(
                f'Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line}\n')

    logger.info(
        f"Generated subtitles with {total_lines} lines from transcript")

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
