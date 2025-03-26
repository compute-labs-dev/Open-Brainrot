from utils.scraping import *
from utils.audio import *
from generators.force_alignment import *
from utils.dict import *
from generators.video_generator import *
from utils.search import *
from generators.brainrot_generator import transform_to_brainrot, MODELS, VOICES, VOICE_PROMPTS
import time
from datetime import datetime, timedelta
import os
import shutil
import boto3
from botocore.exceptions import ClientError
import logging
import threading
import traceback
import re
import math
from pydub import AudioSegment
import asyncio
from tqdm import tqdm
from botocore.exceptions import NoCredentialsError

# Configure module-level logger to match the server format
logger = logging.getLogger(__name__)

# Configure logging
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def upload_to_s3(file_path, bucket, object_name=None):
    """Upload a file to an S3 bucket

    Args:
        file_path: File to upload
        bucket: Bucket to upload to
        object_name: S3 object name. If not specified then file_path is used

    Returns:
        True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_path
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_path, bucket, object_name)
        return f"https://{bucket}.s3.amazonaws.com/{object_name}"
    except ClientError as e:
        logging.error(e)
        return None


def format_time(seconds):
    """Format seconds to MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


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


def extract_random_segment(input_video, output_video, target_duration):
    """Extract a random segment from a video with the specified duration"""
    # Get total duration of input video
    total_duration = get_duration(input_video)

    # Calculate maximum start time to ensure we can get the full target duration
    max_start = total_duration - target_duration

    if max_start < 0:
        logger.error(
            f"Input video ({total_duration:.2f}s) is shorter than target duration ({target_duration:.2f}s)")
        return None

    # Generate random start time
    start_time = random.uniform(0, max_start)

    # Extract segment using ffmpeg
    try:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),
            '-i', input_video,
            '-t', str(target_duration),
            '-c', 'copy',
            output_video
        ]
        subprocess.run(cmd, check=True)
        logger.info(
            f"Extracted {target_duration:.2f}s segment starting at {start_time:.2f}s")
        return output_video
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract video segment: {str(e)}")
        return None


def main(input_source, llm=False, scraped_url='texts/scraped_url.txt', output_pre='texts/processed_output.txt',
         final_output='texts/oof.txt', speech_final='audio/output_converted.wav', subtitle_path='texts/testing.ass',
         output_path='final/final.mp4', speaker_wav="assets/default.mp3", video_path='assets/videos/minecraft.mp4',
         language="en-us", api_key=None, voice="donald_trump", model="claude", s3_bucket=None, timestamp=None):
    """
    Main function to generate a video from text

    Parameters:
    - input_source: Path to input text file or text content
    - llm: Whether to use LLM for text processing
    - scraped_url: Path to save scraped URL
    - output_pre: Path to save preprocessed output
    - final_output: Path to save final output
    - speech_final: Path to save final speech audio
    - subtitle_path: Path to save subtitles
    - output_path: Path to save output video
    - speaker_wav: Path to speaker audio file
    - video_path: Path to video file
    - language: Language code
    - api_key: API key for OpenAI
    - voice: Voice to use
    - model: Model to use
    - s3_bucket: S3 bucket to upload to
    - timestamp: Timestamp for consistent directory naming
    """
    # Start timing the entire process
    total_start_time = time.time()

    # Initialize variables that might be used later
    s3_url = None  # Initialize s3_url to avoid undefined variable issues
    timing_list = []  # Initialize timing_list to avoid undefined variable issues

    # Get the current thread name for logging context
    thread_name = threading.current_thread().name
    voice_context = f"[{voice}]"

    # Helper function to log with voice context
    def log_info(message):
        logger.info(f"{voice_context} {message}")

    def log_error(message):
        logger.error(f"{voice_context} {message}")

    log_info("Starting video generation pipeline")

    # Create timestamped output directory with voice name
    if timestamp is None:
        timestamp = int(time.time())
    # Include voice name in the directory path for parallel processing
    output_dir = os.path.join('outputs', f'{timestamp}_{voice}')
    os.makedirs(output_dir, exist_ok=True)
    log_info(f"Created output directory: {output_dir}")

    # Define output paths with consistent path handling
    current_date = datetime.now()
    base_filename = f'Mar_{current_date.day}_{current_date.year}_Daily_Brainrot_by_{voice}'
    output_paths = {
        'brainrot_text': os.path.join(output_dir, f'{base_filename}_text.txt'),
        'processed_text': os.path.join(output_dir, f'{base_filename}_processed_text.txt'),
        'audio': os.path.join(output_dir, f'{base_filename}_audio.wav'),
        'audio_converted': os.path.join(output_dir, f'{base_filename}_audio_converted.wav'),
        'subtitle': os.path.join(output_dir, f'{base_filename}_subtitles.ass'),
        'video': os.path.join(output_dir, f'{base_filename}_final.mp4')
    }

    # Store timing information
    step_times = {}

    try:
        # SCRAPING (only if input is a URL)
        log_info("\n=== STEP 1: SCRAPING ===")
        start_time = time.time()
        if input_source.startswith(('http://', 'https://')):  # It's a URL
            if not llm:
                map_request = scrape(input_source)
            else:
                log_info("Using LLM to determine best thread to scrape")
                log_info("-------------------")
                reddit_scrape = scrape_llm(input_source)
                text = vader(reddit_scrape)
                if not api_key:
                    api_key = input("Please input the API key\n")
                map_request = groq(text, api_key)
            log_info(map_request)
            save_map_to_txt(map_request, scraped_url)
            input_file = scraped_url
        else:  # It's a file path with direct text
            input_file = input_source
        step_times['scraping'] = time.time() - start_time
        log_info(
            f"Input processing completed in {format_time(step_times['scraping'])}")

        # BRAINROT TRANSFORMATION
        log_info("\n=== STEP 2: TRANSFORMING TO BRAINROT STYLE ===")
        start_time = time.time()
        brainrot_text, output_paths = transform_to_brainrot(
            input_file, api_key, voice, model, timestamp=timestamp)
        step_times['brainrot_transform'] = time.time() - start_time
        log_info(
            f"Brainrot transformation completed in {format_time(step_times['brainrot_transform'])}")

        # AUDIO CONVERSION
        log_info("\n=== STEP 3: AUDIO CONVERSION ===")
        start_time = time.time()
        audio_wrapper(output_paths['brainrot_text'],
                      file_path=output_paths['audio'], voice=voice)
        convert_audio(output_paths['audio'], output_paths['audio_converted'])

        # Add a small silence at the beginning of the audio to help with subtitle synchronization
        log_info(
            "Adding initial silence to audio for better subtitle synchronization")
        add_initial_silence(
            output_paths['audio_converted'], silence_duration=300)

        step_times['audio_conversion'] = time.time() - start_time
        log_info(
            f"Audio conversion completed in {format_time(step_times['audio_conversion'])}")

        # Get audio duration for video segment extraction
        audio_duration = get_audio_duration(output_paths['audio_converted'])
        log_info(f"Audio duration: {format_time(audio_duration)}")

        # Extract video segment matching audio duration
        log_info("\n=== STEP 4: EXTRACTING VIDEO SEGMENT ===")
        start_time = time.time()
        temp_video = os.path.join(output_dir, "temp_video_segment.mp4")
        if not extract_random_segment(video_path, temp_video, audio_duration):
            log_error("Failed to extract video segment")
            raise Exception("Video segment extraction failed")
        step_times['video_extraction'] = time.time() - start_time
        log_info(
            f"Video segment extraction completed in {format_time(step_times['video_extraction'])}")

        # Generate subtitles
        log_info("\n=== STEP 5: GENERATING SUBTITLES ===")
        start_time = time.time()

        # Read the brainrot text and split into sentences
        with open(output_paths['brainrot_text'], 'r', encoding='utf-8') as f:
            text = f.read().strip()

        # Split text into sentences using multiple delimiters
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Further split long sentences into smaller chunks
        chunks = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 10:  # If sentence is too long
                # Split into chunks of 5-10 words
                for i in range(0, len(words), 8):
                    chunk = ' '.join(words[i:i+8])
                    if chunk:
                        chunks.append(chunk)
            else:
                chunks.append(sentence)

        # Calculate timing for each chunk
        total_chunks = len(chunks)
        initial_silence = 0.3  # 300ms initial silence
        subtitle_gap = 0.2  # 200ms gap between subtitles
        available_duration = audio_duration - \
            initial_silence - (subtitle_gap * (total_chunks - 1))
        time_per_chunk = available_duration / total_chunks

        # Write subtitles in ASS format
        with open(output_paths['subtitle'], 'w', encoding='utf-8') as f:
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
            f.write(
                'Style: Default,Arial,48,&HFFFFFF,&H000000,&H000000,&H000000,1,0,0,0,100,100,0,0,1,2,2,2,20,20,20,1\n\n')

            # Write events
            f.write('[Events]\n')
            f.write(
                'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

            # Write dialogue lines with proper timing
            current_time = initial_silence  # Start after initial silence
            for chunk in chunks:
                start_time = current_time
                end_time = start_time + time_per_chunk
                current_time = end_time + subtitle_gap  # Add gap for next subtitle

                # Format times as H:MM:SS.cc for ASS format
                start_str = f"{int(start_time//3600)}:{int((start_time % 3600)//60):02d}:{int(start_time % 60):02d}.{int((start_time % 1)*100):02d}"
                end_str = f"{int(end_time//3600)}:{int((end_time % 3600)//60):02d}:{int(end_time % 60):02d}.{int((end_time % 1)*100):02d}"

                # Write dialogue line in ASS format
                f.write(
                    f'Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{chunk}\n')

        step_times['subtitle_generation'] = time.time() - start_time
        log_info(
            f"Subtitle generation completed in {format_time(step_times['subtitle_generation'])}")
        log_info(
            f"Generated subtitles with {total_chunks} chunks from transcript")

        # VIDEO GENERATION
        log_info("\n=== STEP 6: VIDEO GENERATION ===")
        start_time = time.time()

        # Generate final video with subtitles and audio
        add_subtitles_and_overlay_audio(temp_video, output_paths['audio_converted'],
                                        output_paths['subtitle'], output_paths['video'])

        step_times['video_generation'] = time.time() - start_time
        log_info(
            f"Video generation completed in {format_time(step_times['video_generation'])}")

        # Validate video duration matches audio duration
        final_video_duration = get_duration(output_paths['video'])
        log_info(f"Final video duration: {format_time(final_video_duration)}")
        log_info(f"Audio duration: {format_time(audio_duration)}")

        if abs(final_video_duration - audio_duration) <= 3:  # Allow 3 second margin
            log_info("✅ SUCCESS: Video duration matches audio duration!")
        else:
            log_error(
                f"❌ WARNING: Video duration ({format_time(final_video_duration)}) doesn't match audio duration ({format_time(audio_duration)})")

        # After video generation is complete and successful
        if s3_bucket and os.path.exists(output_paths['video']):
            log_info("\n=== STEP 7: UPLOADING TO S3 ===")
            start_time = time.time()

            # Upload to S3
            s3_object_name = f"videos/{os.path.basename(output_paths['video'])}"
            s3_url = upload_to_s3(
                output_paths['video'], s3_bucket, s3_object_name)

            if s3_url:
                log_info(f"Video uploaded successfully to S3: {s3_url}")
                step_times['s3_upload'] = time.time() - start_time
                log_info(
                    f"S3 upload completed in {format_time(step_times['s3_upload'])}")
            else:
                log_error("Failed to upload video to S3")

        # FINAL SUMMARY
        total_time = time.time() - total_start_time
        log_info("\n=== GENERATION SUMMARY ===")
        log_info(f"Total processing time: {format_time(total_time)}")
        for step, duration in step_times.items():
            log_info(
                f"  - {step}: {format_time(duration)} ({duration / total_time * 100:.1f}%)")

        return output_paths['video'], s3_url if s3_bucket else None

    except Exception as e:
        log_error(f"Error in video generation pipeline: {str(e)}")
        log_error(traceback.format_exc())
        raise


def convert_simple_timing_to_ass(timing_list, output_file):
    """
    Convert a timing list to ASS subtitle format for better visibility
    """
    if not timing_list:
        print("Warning: Empty timing list, creating default subtitle file")
        create_empty_subtitle_file(output_file)
        return

    # Set up ASS file header with improved styling
    header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Group words into phrases for better readability
    max_words_per_phrase = 5  # Increased from 3 to 5 for better flow
    print(f"Max words per phrase: {max_words_per_phrase}")

    phrases = []
    current_phrase = []
    current_start = 0

    for item in timing_list:
        if len(current_phrase) == 0:
            current_start = item['start']

        current_phrase.append(item)

        if len(current_phrase) >= max_words_per_phrase:
            phrases.append({
                'start': current_start,
                'end': current_phrase[-1]['end'],
                'words': [w['word'] for w in current_phrase]
            })
            current_phrase = []

    # Add any remaining words
    if current_phrase:
        phrases.append({
            'start': current_start,
            'end': current_phrase[-1]['end'],
            'words': [w['word'] for w in current_phrase]
        })

    print(f"Estimated phrases: {len(phrases)}")

    # Convert to ASS dialogue lines
    dialogue_lines = []

    for phrase in phrases:
        start_time = convert_seconds_to_ass_time(phrase['start'])
        end_time = convert_seconds_to_ass_time(phrase['end'])

        # Join the words with spaces, and add the dialogue line
        text = ' '.join(phrase['words'])

        # Simple sentence capitalization
        if text and len(text) > 0:
            text = text[0].upper() + text[1:]

        dialogue_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
        dialogue_lines.append(dialogue_line)

    # Write to the output file
    with open(output_file, 'w') as f:
        f.write(header)
        for line in dialogue_lines:
            f.write(line + '\n')

    print(
        f"Created subtitle file at {output_file} with {len(phrases)} phrases")


def create_empty_subtitle_file(output_file):
    """Create an empty subtitle file with a placeholder message"""
    header = """[Script Info]
Title: Default Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,No subtitle data available
"""
    with open(output_file, 'w') as f:
        f.write(header)
    print(f"Created empty subtitle file at {output_file}")


def format_time_ass(seconds):
    """Format time in ASS format (H:MM:SS.cc)"""
    if isinstance(seconds, str):
        return seconds

    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"


def add_initial_silence(audio_path, output_path=None, silence_duration=300):
    """Add a short silence at the beginning of an audio file.

    Args:
        audio_path: Path to the input audio file
        output_path: Path to save the modified audio. If None, modifies in place.
        silence_duration: Duration of silence to add in milliseconds (default: 300ms)

    Returns:
        Path to the modified audio file
    """
    if output_path is None:
        output_path = audio_path

    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Create silence segment
    silence = AudioSegment.silent(duration=silence_duration)

    # Add silence to the beginning
    modified_audio = silence + audio

    # Export the modified audio
    modified_audio.export(
        output_path, format=os.path.splitext(output_path)[1][1:])

    return output_path


def convert_seconds_to_ass_time(seconds):
    """Convert seconds to ASS time format (H:MM:SS.cc)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    centiseconds = int((seconds % 1) * 100)
    seconds = int(seconds)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
