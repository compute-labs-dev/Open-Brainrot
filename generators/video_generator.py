import subprocess
import os
import math
import gentle
import re
import json
import random
from pathlib import Path
from generators.brainrot_generator import transform_to_brainrot, clean_text_for_tts
from pydub import AudioSegment
from utils.logger import log_info, log_error
from constants import SUBTITLE_STYLE, FFMPEG_PARAMS

# ===== SUBTITLE STYLE CONFIGURATION =====
SUBTITLE_STYLES = {
    "Default": {
        "font_name": "Arial",
        "font_size": 80,
        "primary_color": "&H00FFFFFF",  # White (AABBGGRR format)
        "secondary_color": "&H000000FF",  # Red outline
        "outline_color": "&H00000000",   # Black outline
        "back_color": "&H00000000",      # Black shadow
        "bold": 1,                      # 1 for true, 0 for false
        "italic": 0,
        "underline": 0,
        "strike_out": 0,
        "scale_x": 100,
        "scale_y": 100,
        "spacing": 0,
        "angle": 0,
        "border_style": 1,
        "outline": 1,                    # Outline thickness
        "shadow": 0,                     # Shadow distance
        "alignment": 2,                  # 2 for bottom center
        "margin_l": 20,                  # Left margin
        "margin_r": 20,                  # Right margin
        "margin_v": 60,                  # Vertical margin from top
    },
    "Effects": {
        "font_name": "Arial",
        "font_size": 80,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H000000FF",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": 1,
        "italic": 0,
        "underline": 0,
        "strike_out": 0,
        "scale_x": 100,
        "scale_y": 100,
        "spacing": 0,
        "angle": 0,
        "border_style": 1,
        "outline": 0,
        "shadow": 0,
        "alignment": 8,                  # 8 for top center
        "margin_l": 20,                  # Left margin
        "margin_r": 20,                  # Right margin
        "margin_v": 60,                  # Vertical margin
    }
}

# Video dimensions for subtitle positioning
VIDEO_CONFIG = {
    "width": 608,      # 9:16 ratio width
    "height": 1080,    # Standard height
    "fps": 60,
}

# ===== HELPER FUNCTIONS =====


def generate_ass_style_line(style_name, style_config):
    """Generate ASS style line from configuration"""
    return (
        f"Style: {style_name},{style_config['font_name']},{style_config['font_size']},"
        f"{style_config['primary_color']},{style_config['secondary_color']},"
        f"{style_config['outline_color']},{style_config['back_color']},"
        f"{style_config['bold']},{style_config['italic']},{style_config['underline']},"
        f"{style_config['strike_out']},{style_config['scale_x']},{style_config['scale_y']},"
        f"{style_config['spacing']},{style_config['angle']},{style_config['border_style']},"
        f"{style_config['outline']},{style_config['shadow']},{style_config['alignment']},"
        f"{style_config['margin_l']},{style_config['margin_r']},{style_config['margin_v']},1"
    )


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
    """Crop video to 9:16 aspect ratio (vertical video) using dimensions from VIDEO_CONFIG"""
    # Get width and height from VIDEO_CONFIG
    target_width = VIDEO_CONFIG["width"]
    target_height = VIDEO_CONFIG["height"]

    # Create proper 9:16 aspect ratio
    subprocess.run([
        'ffmpeg',
        '-i', input_path,
        # This maintains the height and adjusts width for 9:16 ratio
        '-vf', f'crop=ih*9/16:ih,scale={target_width}:{target_height}',
        '-c:v', FFMPEG_PARAMS["video_codec"],
        '-preset', FFMPEG_PARAMS["preset"],
        '-crf', str(FFMPEG_PARAMS["crf"]),
        '-c:a', 'copy',
        '-y',
        output_path
    ], check=True)

    log_info(f"Cropped video to 9:16 ratio: {target_width}x{target_height}")
    return output_path


# ===== SUBTITLE PROCESSING FUNCTIONS =====

class SubtitleEntry:
    """A class representing a single subtitle entry with timing and text"""

    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return f"SubtitleEntry({self.start_time:.2f}-{self.end_time:.2f}: '{self.text}')"


def format_time_ass(seconds):
    """Format time in ASS format (H:MM:SS.cc)"""
    if isinstance(seconds, str):
        return seconds

    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"


def parse_ass_subtitles(subtitle_path):
    """Parse an ASS subtitle file and return a list of SubtitleEntry objects"""
    if not os.path.exists(subtitle_path) or os.path.getsize(subtitle_path) == 0:
        print(
            f"Warning: Subtitle file {subtitle_path} does not exist or is empty")
        return []

    dialogue_entries = []

    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            subtitle_content = f.read()

        # Extract dialogue lines
        for line in subtitle_content.splitlines():
            if line.startswith('Dialogue:'):
                # Split only first 9 commas to keep text intact
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    layer, start_time, end_time = parts[0:3]
                    text = parts[9]

                    # Convert ASS time format (H:MM:SS.cc) to seconds
                    def time_to_seconds(time_str):
                        h, m, s = time_str.split(':')
                        return float(h) * 3600 + float(m) * 60 + float(s)

                    start_sec = time_to_seconds(start_time)
                    end_sec = time_to_seconds(end_time)

                    dialogue_entries.append(
                        SubtitleEntry(text, start_sec, end_sec))

                print(
                    f"Successfully parsed {len(dialogue_entries)} subtitle entries from ASS file")
    except Exception as e:
        print(f"Error parsing subtitle file: {str(e)}")

    return dialogue_entries


def create_fallback_subtitles():
    """Create fallback subtitles for testing"""
    test_texts = [
        "This is subtitle 1 - Testing visibility",
        "This is subtitle 2 - Should appear after subtitle 1",
        "This is subtitle 3 - One subtitle at a time",
        "This is subtitle 4 - Final test subtitle"
    ]

    dialogue_entries = []
    for i, text in enumerate(test_texts):
        # Each subtitle appears for 5 seconds with 1 second gap
        start_time = i * 6
        end_time = start_time + 5
        dialogue_entries.append(SubtitleEntry(text, start_time, end_time))

    return dialogue_entries


def create_non_overlapping_subtitles(entries):
    """Ensure subtitles don't overlap by adjusting end times"""
    if not entries:
        return []

    # Sort entries by start time to ensure proper ordering
    sorted_entries = sorted(entries.copy(), key=lambda e: e.start_time)

    # Adjust end times to prevent overlap
    for i in range(len(sorted_entries) - 1):
        if sorted_entries[i].end_time > sorted_entries[i+1].start_time:
            # If current entry overlaps with next, cut off at start of next
            sorted_entries[i].end_time = sorted_entries[i+1].start_time

            # Add a small gap between subtitles for better readability (0.2 seconds)
            if sorted_entries[i].end_time > 0.2:
                sorted_entries[i].end_time -= 0.2

    return sorted_entries


def generate_ffmpeg_filters(subtitle_entries, font_size=80, font_path="/System/Library/Fonts/Helvetica.ttc"):
    """Generate FFmpeg drawtext filters for subtitle entries"""
    filter_complex = []

    for i, entry in enumerate(subtitle_entries):
        # Clean text for FFmpeg drawtext filter
        clean_text = entry.text.replace("'", "'\\''").replace(
            ":", "\\:").replace(",", "\\,")

        # Create a complex condition that ensures only one subtitle shows at a time
        # Position subtitle in center of screen both horizontally and vertically
        filter_text = (
            f"drawtext=fontfile={font_path}:fontsize={font_size}:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:text='{clean_text}':"
            f"enable='between(t,{entry.start_time},{entry.end_time})'"
        )

        filter_complex.append(filter_text)

    # Join all filters with commas
    filter_string = ','.join(filter_complex)

    return filter_string


def add_subtitles_and_overlay_audio(
    input_video_path,
    subtitle_file_path,
    audio_file_path,
    output_path,
    temp_dir,
    font_size=None,  # Optional override for font_size from constants
    font_name=None,  # Optional override for font_name from constants
    margin_v=None,   # Optional override for margin_v from constants
    margin_h=None,   # Optional override for margin_h (horizontal margin)
    outline=None,    # Optional override for outline width from constants
    shadow=None,     # Optional override for shadow depth from constants
    bg_opacity=None,  # Optional override for background opacity from constants
    position=None,   # Optional override for position from constants
    border_style=None  # Optional override for border_style from constants
):
    """
    Add subtitle and audio to a video.

    Args:
        input_video_path (str): Path to the input video
        subtitle_file_path (str): Path to the subtitle file in ASS format
        audio_file_path (str): Path to the audio file
        output_path (str): Path to write output video
        temp_dir (str): Path to temporary directory for intermediate files
        font_size (int, optional): Override font size from constants
        font_name (str, optional): Override font name from constants
        margin_v (int, optional): Override vertical margin from constants
        margin_h (int, optional): Override horizontal margin from constants
        outline (float, optional): Override outline width from constants
        shadow (float, optional): Override shadow depth from constants 
        bg_opacity (float, optional): Override background opacity from constants
        position (int, optional): Override position from constants
        border_style (int, optional): Override border style from constants

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a custom style string if any overrides were provided
        custom_style = None
        if any([font_size, font_name, margin_v, margin_h, outline, shadow, bg_opacity, position, border_style]):
            # Start with defaults from constants
            style_params = {
                'font_size': font_size or SUBTITLE_STYLE['font_size'],
                'font_name': font_name or SUBTITLE_STYLE['font_name'],
                'margin_v': margin_v or SUBTITLE_STYLE['margin_v'],
                'margin_l': margin_h or SUBTITLE_STYLE['margin_l'],
                'margin_r': margin_h or SUBTITLE_STYLE['margin_r'],
                'outline': outline or SUBTITLE_STYLE['outline'],
                'shadow': shadow or SUBTITLE_STYLE['shadow'],
                'bg_opacity': bg_opacity if bg_opacity is not None else SUBTITLE_STYLE['bg_opacity'],
                'position': position or SUBTITLE_STYLE['alignment'],
                'border_style': border_style or SUBTITLE_STYLE['border_style']
            }

            # Create the custom ASS style string with overrides
            custom_style = (f"FontName={style_params['font_name']}:"
                            f"FontSize={style_params['font_size']}:"
                            f"PrimaryColour={SUBTITLE_STYLE['primary_color']}:"
                            f"SecondaryColour={SUBTITLE_STYLE['secondary_color']}:"
                            f"OutlineColour={SUBTITLE_STYLE['outline_color']}:"
                            f"BackColour={SUBTITLE_STYLE['back_color']}:"
                            f"Bold=1:Italic=0:"
                            f"BorderStyle={style_params['border_style']}:"
                            f"Outline={style_params['outline']}:"
                            f"Shadow={style_params['shadow']}:"
                            f"Alignment={style_params['position']}:"
                            f"MarginL={style_params['margin_l']}:"
                            f"MarginR={style_params['margin_r']}:"
                            f"MarginV={style_params['margin_v']}")

        # FFmpeg command to add subtitles and audio
        output_with_sub_path = os.path.join(temp_dir, "output_with_sub.mp4")

        # Construct subtitle filter based on whether we have a custom style
        if custom_style:
            subtitle_filter = f"subtitles={subtitle_file_path}:force_style='{custom_style}'"
        else:
            subtitle_filter = f"subtitles={subtitle_file_path}"

        # Add subtitles first
        subtitle_cmd = [
            "ffmpeg",
            "-i", input_video_path,
            "-vf", subtitle_filter,
            "-c:v", FFMPEG_PARAMS["video_codec"],
            "-preset", FFMPEG_PARAMS["preset"],
            "-crf", str(FFMPEG_PARAMS["crf"]),
            "-c:a", "copy",
            "-y", output_with_sub_path
        ]

        log_info(f"Running subtitle command: {' '.join(subtitle_cmd)}")
        subprocess.run(subtitle_cmd, check=True)

        # Then overlay audio
        audio_cmd = [
            "ffmpeg",
            "-i", output_with_sub_path,
            "-i", audio_file_path,
            "-c:v", "copy",
            "-c:a", FFMPEG_PARAMS["audio_codec"],
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y", output_path
        ]

        log_info(f"Running audio overlay command: {' '.join(audio_cmd)}")
        subprocess.run(audio_cmd, check=True)

        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Error in video processing: {str(e)}")
        return False
    except Exception as e:
        log_error(f"Unexpected error in video processing: {str(e)}")
        return False


def extend_video(video_path, temp_dir, target_duration, video_duration):
    """Extend a video by looping to reach target duration"""
    temp_extended_video = os.path.join(temp_dir, "temp_extended_video.mp4")

    # Calculate the number of loops needed (round up)
    loops_needed = math.ceil(target_duration / video_duration)

    # Create a temporary file list for concat
    concat_file = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_file, 'w') as f:
        for _ in range(loops_needed):
            f.write(f"file '{os.path.abspath(video_path)}'\n")

    # Concatenate the video with itself multiple times
    concat_cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        temp_extended_video
    ]
    subprocess.run(concat_cmd, check=True)
    print(f"Extended video created with duration for {loops_needed} loops")

    return temp_extended_video


def ensure_matching_duration(video_path, target_duration, temp_dir):
    """Ensure video duration matches the target duration with a smooth ending"""
    video_duration = get_duration(video_path)

    # Add a longer buffer (1 second) for a smoother ending
    target_duration_with_buffer = target_duration + 1.0

    if abs(video_duration - target_duration_with_buffer) > 0.1:  # Tighter tolerance
        print(
            f"Video duration ({video_duration:.2f}s) doesn't match target duration with buffer ({target_duration_with_buffer:.2f}s)")
        print(f"Adjusting video duration for smoother ending...")

        # Create temp file for the adjusted video
        temp_adjusted = os.path.join(temp_dir, "temp_adjusted.mp4")

        # Use ffmpeg to extend the video
        trim_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            # Duration in seconds with buffer
            '-t', str(target_duration_with_buffer),
            '-c:v', 'copy', '-c:a', 'copy',
            temp_adjusted
        ]
        subprocess.run(trim_cmd, check=True)

        # Replace the output file with the adjusted version
        os.replace(temp_adjusted, video_path)
        print(f"✓ Successfully adjusted video duration for smoother ending")
    else:
        print(f"✓ Video duration already matches target duration with buffer")


def generate_subtitles(audio_path, text, output_path, voice="donald_trump", model="claude", api_key=None):
    """Generate subtitles for a video based on audio and text."""
    print(f"\n=== GENERATING SUBTITLES ===")

    # Process the input text
    transformed_text = process_input_text(
        text, output_path, voice, model, api_key)

    # Create a temporary directory for gentle's output
    temp_dir = os.path.dirname(output_path)
    os.makedirs(temp_dir, exist_ok=True)

    # Get audio duration
    audio_duration = get_duration(audio_path)
    print(f"Audio duration: {audio_duration:.2f} seconds")

    # Try different methods to generate subtitle timing
    try:
        # First attempt: Gentle forced alignment
        subtitle_entries = generate_subtitles_with_gentle(
            audio_path, transformed_text, temp_dir)

        if not subtitle_entries:
            # Second attempt: Simple timing based on word count
            subtitle_entries = generate_subtitles_with_simple_timing(
                transformed_text, audio_duration)
    except Exception as e:
        print(f"Error in subtitle generation: {str(e)}")
        subtitle_entries = generate_subtitles_with_simple_timing(
            transformed_text, audio_duration)

    # Create ASS subtitle file with improved styling
    create_ass_subtitle_file(subtitle_entries, output_path, audio_duration)

    return output_path


def process_input_text(text, output_path, voice, model, api_key):
    """Process input text for subtitle generation"""
    if model == "bypass_transform":
        print("Bypassing text transformation, using provided text directly")
        return text

    print(f"Using {model} to transform text for {voice}")
    text_path = os.path.join(os.path.dirname(output_path), f"{voice}_text.txt")

    try:
        # Save original text
        with open(text_path, 'w') as f:
            f.write(text)

        # Transform text if not already in the right format for the voice
        if model != "bypass_transform":
            transformed_text, _ = transform_to_brainrot(
                text_path, api_key=api_key, voice=voice, model=model)
        else:
            transformed_text = text

        # Clean text for subtitle generation using clean_text
        from dict import clean_text
        cleaned_text = clean_text(transformed_text)
        return cleaned_text

    except Exception as e:
        print(f"Error in text processing: {str(e)}")
        print("Using original text for subtitles")
        from dict import clean_text
        return clean_text(text)


def generate_subtitles_with_gentle(audio_path, text, temp_dir):
    """Generate subtitles using Gentle forced alignment"""
    print("Attempting to generate subtitles with Gentle forced alignment...")
    json_output = os.path.join(temp_dir, "alignment.json")

    try:
        # Use Gentle for forced alignment
        resources = gentle.Resources()
        with gentle.resampled(audio_path) as wavfile:
            aligner = gentle.ForcedAligner(resources, text)
            result = aligner.transcribe(wavfile)

        # Save alignment to JSON
        with open(json_output, 'w') as f:
            f.write(result.to_json())

        # Process the alignment data
        with open(json_output, 'r') as f:
            alignment_data = json.load(f)

        # Build word timings
            entries = []
        for word in alignment_data.get('words', []):
            if word.get('case') == 'success':
                start = word.get('start', 0)
                end = word.get('end', 0)
                word_text = word.get('word', '')

                # Advance subtitles by 0.3 seconds for better synchronization
                start_advanced = max(0, start - 0.3)
                end_advanced = max(0, end - 0.3)

                entries.append(SubtitleEntry(
                    word_text, start_advanced, end_advanced))

        # Group words into phrases
            return group_words_into_phrases(entries)

    except Exception as e:
        print(f"Error in Gentle alignment: {str(e)}")
        return []


def group_words_into_phrases(word_entries, max_duration=2.5, max_words=4):
    """Group words into phrases for better subtitle display"""
    phrases = []
    current_phrase = []
    current_start = None
    current_end = None

    for entry in word_entries:
        if not current_phrase:
            current_start = entry.start_time
            current_phrase.append(entry.text)
            current_end = entry.end_time
        elif entry.end_time - current_start <= max_duration and len(current_phrase) < max_words:
            current_phrase.append(entry.text)
            current_end = entry.end_time
        else:
            phrases.append(SubtitleEntry(
                ' '.join(current_phrase), current_start, current_end))
            current_phrase = [entry.text]
            current_start = entry.start_time
            current_end = entry.end_time

    # Add the last phrase if there is one
    if current_phrase:
        phrases.append(SubtitleEntry(
            ' '.join(current_phrase), current_start, current_end))

    return phrases


def generate_subtitles_with_simple_timing(text, audio_duration):
    """Generate subtitles with simple timing based on word count"""
    print("Using simple timing method for subtitle generation...")

    # Split text into sentences first
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Calculate base timing
    total_sentences = len(sentences)
    avg_time_per_sentence = audio_duration / total_sentences

    entries = []
    current_time = 0

    # Create subtitles for each sentence
    for i, sentence in enumerate(sentences):
        # Split sentence into words
        words = sentence.split()

        # Calculate timing for this sentence
        start_time = current_time
        end_time = start_time + avg_time_per_sentence

        # Ensure we don't exceed audio duration
        end_time = min(end_time, audio_duration)

        # Create subtitle entry
        entries.append(SubtitleEntry(sentence, start_time, end_time))

        # Update current time for next sentence
        current_time = end_time

        # Add a small gap between sentences
        if i < len(sentences) - 1:  # Don't add gap after the last sentence
            current_time += 0.2  # 0.2 second gap between sentences

    # Ensure no overlaps and proper spacing
    for i in range(len(entries) - 1):
        # If current subtitle overlaps with next one
        if entries[i].end_time > entries[i + 1].start_time:
            # Add a small gap between subtitles
            gap = 0.1
            entries[i].end_time = entries[i + 1].start_time - gap

    return entries


def create_ass_subtitle_file(subtitle_entries, output_path, audio_duration):
    """Create an ASS subtitle file from subtitle entries"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write('[Script Info]\n')
        f.write('Title: Generated Subtitles\n')
        f.write('ScriptType: v4.00+\n')
        f.write('WrapStyle: 0\n')
        f.write('ScaledBorderAndShadow: yes\n')
        f.write('YCbCr Matrix: TV.601\n')
        f.write(f'PlayResX: {VIDEO_CONFIG["width"]}\n')
        f.write(f'PlayResY: {VIDEO_CONFIG["height"]}\n\n')

        # Write styles
        f.write('[V4+ Styles]\n')
        f.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')

        # Write each style from configuration
        for style_name, style_config in SUBTITLE_STYLES.items():
            f.write(generate_ass_style_line(style_name, style_config) + '\n')
        f.write('\n')

        # Write events
        f.write('[Events]\n')
        f.write(
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

        # Write dialogue lines
        for entry in subtitle_entries:
            start_time = format_time_ass(entry.start_time)
            end_time = format_time_ass(entry.end_time)

            # Determine if this is a special effect
            is_effect = entry.text.startswith('(') and entry.text.endswith(')')
            style = "Effects" if is_effect else "Default"

            # For effects, make them invisible
            if is_effect:
                text = "{\\alpha&HFF&}" + entry.text
            else:
                text = entry.text

                f.write(
                    f'Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}\n')

        # Add a final empty subtitle if needed to match audio duration
        if subtitle_entries:
            last_subtitle_end = subtitle_entries[-1].end_time
            if last_subtitle_end < audio_duration - 0.5:  # If gap is more than 0.5 seconds
                final_start = format_time_ass(last_subtitle_end)
                final_end = format_time_ass(audio_duration)
                f.write(
                    f'Dialogue: 0,{final_start},{final_end},Default,,0,0,0,,\n')
                print(
                    f"Added final empty subtitle from {last_subtitle_end:.2f} to {audio_duration:.2f} seconds")

    print(f"Created subtitle file at: {output_path}")
    return output_path


def ensure_strictly_sequential_subtitles(entries):
    """
    Ensure subtitles appear one after another with no overlap
    This is different from create_non_overlapping_subtitles because it enforces
    strict sequencing regardless of original timing

    Also breaks up longer subtitles into smaller chunks for faster-paced style
    """
    if not entries:
        return []

    # Voice-specific timing adjustments - different TTS engines have slightly different timing characteristics
    VOICE_SYNC_ADJUSTMENTS = {
        "default": -0.3         # Increased default lead time
    }

    # Try to detect voice from the first entry's text if possible
    voice_hint = None
    if entries and hasattr(entries[0], 'voice'):
        voice_hint = entries[0].voice

    # Apply voice-specific offset or use default
    voice_offset = VOICE_SYNC_ADJUSTMENTS.get(
        voice_hint, VOICE_SYNC_ADJUSTMENTS['default'])

    # Sort entries by start time to ensure proper ordering
    sorted_entries = sorted(entries.copy(), key=lambda e: e.start_time)

    # Break up longer entries into smaller chunks (for faster pace)
    chunked_entries = []
    for entry in sorted_entries:
        # If text is long enough to split
        text = entry.text.strip()

        # Detect if entry contains a question - questions need more time
        is_question = '?' in text

        # Look for natural breaking points (punctuation marks)
        punctuation_breaks = [
            i for i, char in enumerate(text) if char in '.,:;-']

        words = text.split()
        if len(words) > 4:
            # Calculate duration per chunk
            total_duration = entry.end_time - entry.start_time

            # Determine optimal chunk size based on content
            if is_question:
                chunk_size = 2  # Smaller chunks for questions (need more time)
            elif any(len(word) > 8 for word in words):
                chunk_size = 2  # Smaller chunks for content with long words
            else:
                chunk_size = 3  # Default chunk size

            num_chunks = (len(words) + chunk_size -
                          1) // chunk_size  # Ceiling division
            chunk_duration = total_duration / num_chunks

            # Create chunks
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i+chunk_size]
                chunk_text = ' '.join(chunk_words)

                # Calculate smart preview buffer based on content
                content_complexity = sum(
                    len(word) for word in chunk_words) / (5 * len(chunk_words))
                # Increased preview buffer
                preview_buffer = 0.3 + (0.15 * min(1.0, content_complexity))

                # Calculate start time with voice-specific adjustment
                chunk_start = max(0, entry.start_time + (i // chunk_size)
                                  * chunk_duration + voice_offset - preview_buffer)

                # Dynamic duration based on content
                duration_factor = 1.0
                if is_question:
                    duration_factor = 1.2  # Questions need more time
                elif any(len(word) > 8 for word in chunk_words):
                    duration_factor = 1.15  # Long words need more time

                # Apply dynamic duration with minimum duration
                adjusted_duration = max(0.6, chunk_duration * duration_factor)
                chunk_end = chunk_start + adjusted_duration

                chunked_entries.append(SubtitleEntry(
                    chunk_text, chunk_start, chunk_end))
        else:
            # Keep short entries as they are, but add smart preview buffer
            complexity = sum(len(word)
                             for word in words) / (5 * max(1, len(words)))
            # Increased preview buffer
            preview_buffer = 0.3 + (0.15 * min(1.0, complexity))

            # Apply voice-specific adjustment with preview buffer
            adjusted_start = max(0, entry.start_time +
                                 voice_offset - preview_buffer)

            # Determine optimal duration based on content
            duration_factor = 1.0
            if is_question:
                duration_factor = 1.2
            elif any(len(word) > 8 for word in words):
                duration_factor = 1.15

            # Apply duration with minimum duration
            adjusted_duration = max(
                0.6, (entry.end_time - entry.start_time) * duration_factor)
            modified_entry = SubtitleEntry(
                entry.text,
                adjusted_start,
                adjusted_start + adjusted_duration
            )
            chunked_entries.append(modified_entry)

    # Use the chunked entries instead
    sorted_entries = sorted(chunked_entries, key=lambda e: e.start_time)

    # Add a natural ending sequence
    if sorted_entries:
        last_entry = sorted_entries[-1]

        # Check if the last entry ends with punctuation
        ends_with_punctuation = any(
            last_entry.text.rstrip().endswith(p) for p in '.!?')

        # Calculate ending pause duration based on content
        word_count = len(last_entry.text.split())
        word_complexity = sum(
            len(word) for word in last_entry.text.split()) / max(1, word_count)

        # Give more time for the final subtitle
        if "subscribe" in last_entry.text.lower():
            # Extra time for call-to-action
            base_ending_pause = 1.5
            complexity_factor = 0.5
        else:
            # Longer pause for complex endings or sentences
            base_ending_pause = 1.2 if ends_with_punctuation else 1.0
            complexity_factor = min(0.5, word_complexity * 0.2)

        ending_pause = base_ending_pause + complexity_factor

        # Add a longer breath effect after the last subtitle
        breath_start = last_entry.end_time + 0.3
        breath_duration = 0.5
        breath_entry = SubtitleEntry(
            "(breath)", breath_start, breath_start + breath_duration)
        sorted_entries.append(breath_entry)

        # Add a final pause entry for a smooth ending
        pause_start = breath_start + breath_duration
        pause_duration = ending_pause
        pause_entry = SubtitleEntry(
            "", pause_start, pause_start + pause_duration)
        sorted_entries.append(pause_entry)

    return sorted_entries


def create_srt_subtitle_file(subtitle_entries, output_path):
    """Create an SRT subtitle file from subtitle entries"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header with transparency style
        f.write("""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1
Style: Effects,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")

        for i, entry in enumerate(subtitle_entries):
            # Convert seconds to ASS time format (HH:MM:SS,mmm)
            start_time_str = seconds_to_srt_time(entry.start_time)
            end_time_str = seconds_to_srt_time(entry.end_time)

            # Check if this is a special effect entry (like breath)
            is_effect = entry.text.startswith('(') and entry.text.endswith(')')

            # Use transparent style for effects, regular style for normal text
            style = "Effects" if is_effect else "Default"

            # For effects, make them invisible by using alpha channel
            if is_effect:
                text = "{\\alpha&HFF&}" + entry.text
            else:
                text = entry.text

            # Write subtitle entry
            f.write(
                f"Dialogue: 0,{start_time_str},{end_time_str},{style},,0,0,0,,{text}\n")

    print(f"Created SRT subtitle file with {len(subtitle_entries)} entries")
    return output_path


def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d},{milliseconds:03d}"


def adjust_subtitles_with_silence_data(subtitle_entries, silence_periods, audio_duration):
    """Adjust subtitle timing based on detected silence periods in audio"""
    if not subtitle_entries or not silence_periods:
        return subtitle_entries

    adjusted_entries = subtitle_entries.copy()

    # Find significant pauses (longer than 0.3 seconds)
    significant_pauses = [(start, end)
                          for start, end in silence_periods if end - start > 0.3]

    if not significant_pauses:
        return subtitle_entries

    # Sort entries by start time
    adjusted_entries = sorted(adjusted_entries, key=lambda e: e.start_time)

    # For each subtitle, check if there's a silence period nearby
    for i, entry in enumerate(adjusted_entries):
        # Look for silence periods that overlap with this subtitle timing
        for silence_start, silence_end in significant_pauses:
            # If a silence period starts during this subtitle, try to end the subtitle there
            if entry.start_time < silence_start < entry.end_time:
                # End subtitle at silence start (with small buffer)
                adjusted_entries[i].end_time = silence_start - 0.1
                print(
                    f"Adjusted subtitle {i+1} to end at natural pause: {silence_start:.2f}s")

            # If next subtitle exists and a silence period ends just before it
            if i < len(adjusted_entries) - 1:
                next_subtitle = adjusted_entries[i+1]
                # If silence ends shortly before next subtitle, delay next subtitle to align with speech
                if abs(silence_end - next_subtitle.start_time) < 0.5:
                    time_diff = silence_end - next_subtitle.start_time
                    if time_diff > 0:
                        # Add a small buffer after silence ends
                        adjusted_entries[i+1].start_time = silence_end + 0.1
                        print(
                            f"Delayed subtitle {i+2} to align with speech after pause")

    return adjusted_entries


# Only trim video if this file is run directly
if __name__ == "__main__":
    trim_video('assets/videos/minecraft.mp4',
               'assets/trimed.mp4', duration=120)
