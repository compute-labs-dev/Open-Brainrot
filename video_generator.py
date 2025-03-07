import subprocess
import os
import math
import gentle
import re
from brainrot_generator import transform_to_brainrot, clean_text_for_tts


def get_duration(file_path):
    """Get duration of a media file using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    return float(subprocess.check_output(cmd).decode('utf-8').strip())

# Use this if you need to trim longer videos from sample video


def trim_video(input_path, output_path, duration=120):
    """Trim video to specified duration"""
    # Only trim if output doesn't exist or is older than input
    if not os.path.exists(output_path) or \
       os.path.getmtime(input_path) > os.path.getmtime(output_path):
        command = [
            'ffmpeg',
            '-i', input_path,
            '-t', str(duration),
            '-c', 'copy',
            '-y',  # Overwrite without asking
            output_path
        ]
        subprocess.run(command, check=True)

# Crop video to 9:16 aspect ratio


def crop_to_vertical(input_path, output_path):
    # Get video dimensions
    dimension_cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        input_path
    ]
    dimensions = subprocess.check_output(
        dimension_cmd).decode('utf-8').strip().split('x')
    width = int(dimensions[0])
    height = int(dimensions[1])

    # Calculate crop dimensions for 9:16 ratio
    if width/height > 9/16:  # If video is wider than 9:16
        new_width = int(height * 9/16)
        crop_x = int((width - new_width) / 2)
        crop_command = f"crop={new_width}:{height}:{crop_x}:0"
    else:  # If video is taller than 9:16
        new_height = int(width * 16/9)
        crop_y = int((height - new_height) / 2)
        crop_command = f"crop={width}:{new_height}:0:{crop_y}"

    # Apply crop
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', crop_command,
        '-c:a', 'copy',
        '-y',
        output_path
    ]
    subprocess.run(command, check=True)
    return output_path


def add_subtitles_and_overlay_audio(video_path, audio_path, subtitle_path, output_path):
    """
    Add subtitles and overlay audio to video
    """
    # Get output directory from output_path and convert paths to absolute
    output_dir = os.path.dirname(output_path)
    temp_looped = os.path.join(output_dir, "temp_looped_video.mp4")
    temp_cropped = os.path.join(output_dir, "temp_cropped_video.mp4")
    video_path_abs = os.path.abspath(video_path)

    # Get durations
    video_duration = get_duration(video_path)
    audio_duration = get_duration(audio_path)

    # Calculate how many times to loop the video
    loop_count = math.ceil(audio_duration / video_duration)

    try:
        # Create concatenation file with absolute path
        concat_file = os.path.join(output_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for _ in range(loop_count):
                f.write(f"file '{video_path_abs}'\n")

        # Concatenate video
        subprocess.run([
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy',
            '-y',  # Add -y to overwrite without asking
            temp_looped
        ])

        # Check if video is already in 9:16 format
        dimension_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            video_path
        ]
        dimensions = subprocess.check_output(
            dimension_cmd).decode('utf-8').strip().split('x')
        width = int(dimensions[0])
        height = int(dimensions[1])
        aspect_ratio = width / height

        # If the video is already close to 9:16 ratio (allowing for small variations)
        if 0.55 <= aspect_ratio <= 0.57:  # 9/16 ≈ 0.5625
            # Just trim duration without cropping
            subprocess.run([
                'ffmpeg', '-i', temp_looped, '-t', str(audio_duration),
                '-c:v', 'libx264', '-c:a', 'aac',
                '-y',  # Add -y to overwrite without asking
                temp_cropped
            ])
        else:
            # Apply cropping for non-9:16 videos
            subprocess.run([
                'ffmpeg', '-i', temp_looped, '-t', str(audio_duration),
                '-c:v', 'libx264', '-c:a', 'aac', '-filter:v', 'crop=404:720:438:0',
                '-y',  # Add -y to overwrite without asking
                temp_cropped
            ])

        # Add subtitles and audio
        subprocess.run([
            'ffmpeg', '-i', temp_cropped, '-i', audio_path,
            '-vf', f'subtitles={subtitle_path}',
            '-c:v', 'libx264', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
            '-y',  # Add -y to overwrite without asking
            output_path
        ])

    finally:
        # Clean up temporary files (in finally block to ensure cleanup)
        for temp_file in [concat_file, temp_looped, temp_cropped]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(
                    f"Warning: Could not remove temporary file {temp_file}: {e}")


def generate_subtitles(audio_path, text, output_path, voice="donald_trump", model="claude", api_key=None):
    """Generate subtitles using timing-based alignment with special effects support"""
    # First transform the text using the same model as the audio generation
    brainrot_text, _ = transform_to_brainrot(text, api_key, voice, model)

    # Clean the transformed text for TTS
    cleaned_text = clean_text_for_tts(brainrot_text)

    # Define special effects and their timing impacts (in seconds)
    effect_timing = {
        '(break)': 0.7,        # Short pause (increased from 0.5)
        '(long-break)': 2.0,   # Longer pause (increased from 1.5)
        '(breath)': 0.5,       # Breathing pause (increased from 0.3)
        '(laugh)': 0.8,        # Laughter (slightly increased)
        '(cough)': 0.6,        # Cough (slightly increased)
        '(lip-smacking)': 0.3,  # Lip smacking (slightly increased)
        '(sigh)': 0.6,         # Sigh (increased from 0.4)
        '(burp)': 0.4          # Burp (slightly increased)
    }

    # Split into sentences and normalize
    sentences = []
    current_sentence = []
    current_text = []  # Keep track of actual display text

    # Split text into words and process
    words = cleaned_text.split()
    i = 0
    while i < len(words):
        word = words[i]

        # Check if word is a special effect
        if word in effect_timing:
            # If we have words in the current sentence, add them as a sentence
            if current_sentence:
                # Only clean text for display
                display_text = ' '.join(current_text)
                # Full text including effects
                full_text = ' '.join(current_sentence)
                sentences.append((display_text, full_text, 0))
                current_sentence = []
                current_text = []
            # Add the effect as a timing marker only
            sentences.append(("", word, effect_timing[word]))
        else:
            # For normal words, add to both display and full text
            current_sentence.append(word)
            # Only add to display text if it's not a special effect
            if not any(effect in word for effect in effect_timing):
                current_text.append(word)

            # Check for sentence endings
            if word.endswith(('.', '!', '?')):
                if current_sentence:
                    # Only clean text for display
                    display_text = ' '.join(current_text)
                    # Full text including effects
                    full_text = ' '.join(current_sentence)
                    sentences.append((display_text, full_text, 0))
                    current_sentence = []
                    current_text = []
        i += 1

    # Handle any remaining text
    if current_sentence:
        display_text = ' '.join(current_text)  # Only clean text for display
        full_text = ' '.join(current_sentence)  # Full text including effects
        sentences.append((display_text, full_text, 0))

    # Write ASS subtitle file
    with open(output_path, "w", encoding='utf-8') as f:
        # Write ASS header
        f.write("""[Script Info]
; Script generated by Python script
Title: Default ASS file
ScriptType: v4.00+
PlayResX: 384
PlayResY: 720
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,10,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,0,5,5,5,15,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")

        # Calculate timing based on audio duration
        audio_duration = get_duration(audio_path)

        # Estimate words per second (typical speech rate)
        total_words = sum(len(s[1].split())
                          for s in sentences if s[1] not in effect_timing)
        words_per_second = total_words / audio_duration

        current_time = 0
        for display_text, full_text, effect_duration in sentences:
            # If it's a special effect, add the pause but don't display text
            if full_text in effect_timing:
                current_time += effect_duration
                continue

            # Skip empty display text
            if not display_text.strip():
                continue

            # Calculate duration based on word count and speech rate
            word_count = len(full_text.split())
            duration = (word_count / words_per_second) * 1.1  # Add 10% buffer

            # Ensure reasonable duration bounds
            duration = min(max(duration, 1.5), 4.0)

            start = format_timestamp(current_time)
            end = format_timestamp(current_time + duration)

            # Write the subtitle event with display_text (without effects)
            f.write(
                f'Dialogue: 0,{start},{end},Default,,0,0,0,,{display_text}\n')

            current_time += duration


def format_timestamp(seconds):
    """Convert seconds to ASS timestamp format (H:MM:SS.cc)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds % 1) * 100)
    seconds = int(seconds)
    return f'{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}'


# Only trim video if this file is run directly
if __name__ == "__main__":
    trim_video('assets/minecraft.mp4', 'assets/trimed.mp4', duration=120)
