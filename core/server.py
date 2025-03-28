from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS  # Add CORS support
from core.db_client import SupabaseClient
from utils.audio import VOICE_IDS
from generators.brainrot_generator import MODELS, VOICES, VOICE_PROMPTS
from core.main import main
import os
import tempfile
import traceback  # Add this for better error tracking
from dotenv import load_dotenv
from datetime import datetime
import json
import re
import time
import concurrent.futures
import logging
import threading
import multiprocessing
import uuid
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(processName)s|%(threadName)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load environment variables
load_dotenv()

# Get S3 configuration from environment variables
S3_BUCKET = os.getenv('S3_BUCKET')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Initialize Supabase client
try:
    db = SupabaseClient()
    SUPABASE_ENABLED = True
    print("Supabase client initialized successfully")
    if SUPABASE_ENABLED:
        print(
            f"Supabase URL: {os.getenv('SUPABASE_URL', 'Not set')[:10]}...")
        print(
            f"Supabase Key: {os.getenv('SUPABASE_KEY', 'Not set')[:10]}...")
except Exception as e:
    SUPABASE_ENABLED = False
    print(f"Failed to initialize Supabase client: {e}")

# Available background videos
AVAILABLE_VIDEOS = {
    "minecraft": "assets/videos/minecraft.mp4",
    "subway": "assets/subway.mp4"
}

# Configure AWS credentials if provided
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
    os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
    os.environ['AWS_DEFAULT_REGION'] = AWS_REGION


def check_required_files():
    """Check if all required files and directories exist"""
    required_files = {
        'assets/videos/minecraft.mp4': 'Minecraft background video file',
        'assets/subway.mp4': 'Subway background video file',
        'assets/default.mp3': 'Default audio file'
    }

    required_dirs = {
        'final': 'Output directory',
        'audio': 'Audio directory',
        'texts': 'Text directory',
        'outputs': 'Processing directory'
    }

    # Check for required API keys
    required_env_vars = {
        'OPENAI_API_KEY': 'OpenAI API key (required for text generation)',
        'FISH_API_KEY': 'Fish Audio API key (required for voice generation)'
    }

    missing = []

    for file_path, desc in required_files.items():
        if not os.path.isfile(file_path):
            missing.append(f"{desc} not found at: {file_path}")

    for dir_path, desc in required_dirs.items():
        if not os.path.isdir(dir_path):
            try:
                os.makedirs(dir_path)
                print(f"Created {desc} at: {dir_path}")
            except Exception as e:
                missing.append(
                    f"Could not create {desc} at {dir_path}: {str(e)}")

    # Check environment variables
    for env_var, desc in required_env_vars.items():
        if not os.getenv(env_var):
            missing.append(
                f"Missing {desc} in environment variables: {env_var}")

    return missing


@app.route('/')
def index():
    # Check required files on startup
    missing = check_required_files()
    status_info = {
        "status": "Server running with warnings" if missing else "Server is running",
        "s3_enabled": bool(S3_BUCKET),
        "supabase_enabled": SUPABASE_ENABLED
    }

    if missing:
        status_info["warnings"] = missing

    return jsonify(status_info), 200


# Define process_voice function at module level for multiprocessing compatibility
def process_voice(voice, text, word_count, digest_id, title, description, model, video, temp_path, request_id, use_special_effects=True):
    """Process a single voice generation request"""
    logger.info(f"=== STARTING VOICE GENERATION: {voice} ===")

    # Initialize voice_result to prevent "referenced before assignment" error
    voice_result = {
        'voice': voice,
        'error': None,
        's3_url': ""
    }

    # Create a process-local temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        process_temp_path = f.name
        f.write(text)
        logger.info(
            f"Created process-local temporary file at: {process_temp_path}")

    try:
        # Initialize a new database connection for this process
        local_db = None
        if SUPABASE_ENABLED:
            try:
                local_db = SupabaseClient()
                logger.info(
                    f"Initialized new database connection for process Voice-{voice}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize database connection: {str(e)}")

        # Process the digest_id
        logger.info(f"Received digest_id: {digest_id}")

        # Validate and use the digest_id
        try:
            # Clean up any whitespace or formatting issues
            if digest_id:
                digest_id = digest_id.strip()

            # Try to validate as UUID, but be lenient
            if digest_id:
                try:
                    uuid_obj = uuid.UUID(digest_id)
                    digest_id = str(uuid_obj)  # Normalize format
                except ValueError:
                    logger.warning(
                        f"Invalid digest_id format: {digest_id}, generating new UUID")
                    digest_id = str(uuid.uuid4())
            else:
                logger.warning("No digest_id provided, generating new UUID")
                digest_id = str(uuid.uuid4())

            logger.info(f"Using digest_id: {digest_id}")
        except Exception as e:
            logger.error(f"Error processing digest_id: {str(e)}")
            digest_id = str(uuid.uuid4())

        # Create a record in Supabase if enabled
        video_id = None
        if SUPABASE_ENABLED and local_db:
            logger.info(
                f"Creating Supabase record (SUPABASE_ENABLED: {SUPABASE_ENABLED})")
            try:
                # Create metadata
                metadata = {
                    "model": model,
                    "start_time": datetime.now().isoformat(),
                    "title": f"Daily Digest - {voice.replace('_', ' ').title()}",
                    "description": description or "AI-generated content",
                    "use_special_effects": use_special_effects
                }

                # Create video data
                video_data = {
                    "status": "processing",
                    "word_count": word_count,
                    "s3_url": "",  # Empty placeholder
                    "voice": voice,  # Explicitly set the voice field
                    "background_video": video,
                    "metadata": metadata,
                    "digest_id": digest_id
                }

                # Insert the video record
                result = local_db.insert_video(video_data)

                if result and len(result) > 0:
                    video_id = result[0]["id"]
                    logger.info(f"Created video record with ID: {video_id}")
                else:
                    logger.warning(
                        "No video ID returned from insert operation")
            except Exception as e:
                error_details = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
                logger.error(
                    f"Error creating video record in Supabase: {json.dumps(error_details)}")

                # Check if it's a schema constraint issue
                if "violates not-null constraint" in str(e):
                    logger.error(
                        "Database schema requires non-null values for certain fields")

                logger.info("Continuing without Supabase record...")
                # Generate a temporary ID
                video_id = f"local-{int(time.time())}"
        else:
            # Generate a temporary ID
            video_id = f"local-{int(time.time())}"
            logger.info(f"Supabase disabled, using local ID: {video_id}")

        # Step 4: Generate the video
        logger.info(f"Starting main processing pipeline")
        process_start = datetime.now()

        # Import references for access to global variables
        from core.main import main
        from generators.brainrot_generator import MODELS, VOICES, VOICE_PROMPTS

        # Get the video path
        available_video_path = AVAILABLE_VIDEOS[video]

        # Generate timestamp for consistent directory naming
        timestamp = int(time.time())
        output_dir = f"outputs/{timestamp}_{voice}"

        # Pass the timestamp to main for consistent directory naming
        result = main(process_temp_path, llm=False, voice=voice,
                      model=model, video_path=available_video_path,
                      s3_bucket=S3_BUCKET, timestamp=timestamp,
                      api_key=os.getenv('OPENAI_API_KEY'),
                      use_special_effects=use_special_effects)

        process_end = datetime.now()
        process_duration = (process_end - process_start).total_seconds()
        logger.info(
            f"Video processing completed in {process_duration:.2f} seconds")

        # Unpack the result tuple
        video_path, s3_url = result if isinstance(
            result, tuple) else (result, None)
        logger.info(f"Video generation result path: {video_path}")
        if s3_url:
            logger.info(f"S3 URL: {s3_url}")

        end_time = datetime.now()
        process_duration = (end_time - process_start).total_seconds()

        # Step 5: Process the result
        if os.path.exists(video_path):
            relative_path = os.path.relpath(video_path, os.getcwd())

            # Use S3 URL for video_url if available, otherwise use local path
            if s3_url:
                voice_result = {
                    'voice': voice,
                    'video_url': s3_url,
                    'local_path': f'/{relative_path}',
                    's3_url': s3_url
                }
            else:
                voice_result = {
                    'voice': voice,
                    'video_url': f'/{relative_path}',
                    'local_path': f'/{relative_path}',
                    's3_url': ""
                }

            logger.info(f"Video available at: {relative_path}")

            # Get subtitle file if it exists
            subtitle_file = os.path.splitext(video_path)[0] + ".ass"
            if os.path.exists(subtitle_file):
                relative_subtitle_path = os.path.relpath(
                    subtitle_file, os.getcwd())
                voice_result['subtitle_url'] = f'/{relative_subtitle_path}'
                logger.info(
                    f"Subtitles available at: {relative_subtitle_path}")

            # Get transcript file if it exists
            transcript_file = os.path.join(os.path.dirname(
                video_path), f"Mar_{datetime.now().day}_{datetime.now().year}_Daily_Brainrot_by_{voice.replace('_', ' ').title()}_text.txt")
            if os.path.exists(transcript_file):
                # Read the transcript content
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        transcript_content = f.read()

                    # Store transcript in metadata for database update
                    transcript_preview = transcript_content[:500] + (
                        "..." if len(transcript_content) > 500 else "")
                    transcript_metadata = {
                        "transcript_preview": transcript_preview,
                        "transcript_path": transcript_file
                    }

                    logger.info(f"Found transcript file at: {transcript_file}")
                except Exception as e:
                    logger.error(f"Error reading transcript file: {str(e)}")
                    transcript_metadata = None
            else:
                logger.warning(
                    f"Transcript file not found at: {transcript_file}")
                transcript_metadata = None

            # Update video record in Supabase if enabled
            if SUPABASE_ENABLED and local_db and video_id and video_id.startswith('local-') is False:
                try:
                    logger.info(
                        f"Updating Supabase record {video_id} to 'completed'")
                    metadata = {
                        "model": model,
                        "start_time": process_start.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": process_duration,
                        "voice": voice,
                        "use_special_effects": use_special_effects
                    }

                    # Add transcript metadata if available
                    if transcript_metadata:
                        metadata.update(transcript_metadata)

                    # Update both status and s3_url
                    update_data = {
                        "status": "completed",
                        "metadata": json.dumps(metadata)
                    }

                    # Update s3_url if available
                    if s3_url:
                        update_data["s3_url"] = s3_url
                        logger.info(f"Updating S3 URL in database: {s3_url}")

                    # Update the record
                    response = local_db.supabase.table("videos") \
                        .update(update_data) \
                        .eq("id", video_id) \
                        .execute()

                    logger.info(
                        f"Successfully updated video record with S3 URL")
                except Exception as e:
                    logger.error(
                        f"Error updating video record in Supabase: {str(e)}")
        else:
            logger.error(f"Error: Video file not found at {video_path}")
            voice_result['error'] = "Video file not found"

            # Try to construct an S3 URL anyway for the expected path
            if S3_BUCKET:
                expected_basename = os.path.basename(video_path)
                s3_object_name = f"videos/{expected_basename}"
                constructed_s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_object_name}"
                voice_result['s3_url'] = constructed_s3_url
                logger.info(
                    f"Constructed expected S3 URL despite missing file: {constructed_s3_url}")
            else:
                logger.warning(
                    "S3_BUCKET not configured, cannot construct expected S3 URL")

            # Update Supabase status to failed if enabled
            if SUPABASE_ENABLED and local_db and video_id and video_id.startswith('local-') is False:
                try:
                    logger.info(
                        f"Updating Supabase record {video_id} to 'failed' (file not found)")
                    metadata = {
                        "model": model,
                        "start_time": process_start.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": process_duration,
                        "error": "Video file not found",
                        "use_special_effects": use_special_effects
                    }

                    local_db.update_video_status(
                        video_id, "failed", metadata)
                    logger.info(
                        f"Successfully updated video record to failed status")
                except Exception as e:
                    logger.error(
                        f"Error updating video record in Supabase: {str(e)}")

    except Exception as e:
        # Handle any exceptions in the overall process
        error_details = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        logger.error(f"Error generating video: {json.dumps(error_details)}")

        voice_result['error'] = str(e)

        # Update Supabase status to failed if enabled
        if SUPABASE_ENABLED and local_db and video_id and video_id.startswith('local-') is False:
            try:
                logger.info(
                    f"Updating Supabase record {video_id} to 'failed' (exception)")
                metadata = {
                    "model": model,
                    "start_time": process_start.isoformat() if 'start_time' in locals() else datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "error": str(e),
                    "use_special_effects": use_special_effects
                }

                local_db.update_video_status(
                    video_id, "failed", metadata)
                logger.info(
                    f"Successfully updated video record to failed status")
            except Exception as supabase_error:
                logger.error(
                    f"Error updating video record in Supabase: {str(supabase_error)}")

    finally:
        # Clean up resources
        if process_temp_path and process_temp_path != temp_path:
            try:
                os.remove(process_temp_path)
                logger.info(
                    f"Cleaned up process-local temporary file: {process_temp_path}")
            except Exception as cleanup_error:
                logger.error(
                    f"Error cleaning up process-local temporary file: {str(cleanup_error)}")

    # Final logging
    total_duration = (datetime.now() - process_start).total_seconds()
    logger.info(
        f"=== COMPLETED VOICE GENERATION: {voice} in {total_duration:.2f} seconds ===")
    return voice_result

# Define wrapper function at module level


def process_voice_wrapper(args):
    """Wrapper function for process_voice for use with multiprocessing.

    Args:
        args (tuple): Tuple of arguments for process_voice
    """
    try:
        # Unpack the arguments tuple
        voice, text, word_count, digest_id, title, description, model, video, temp_path, request_id, use_special_effects = args

        print("process_voice_wrapper received parameters:")
        print(f"  voice: {voice}")
        print(f"  digest_id: {digest_id}")
        print(f"  model: {model}")
        print(f"  video: {video}")
        print(f"  use_special_effects: {use_special_effects}")

        # Set a descriptive process name for better monitoring
        multiprocessing.current_process().name = f"Voice-{voice}"

        # Call the main processing function
        return process_voice(voice, text, word_count, digest_id, title, description, model, video, temp_path, request_id, use_special_effects)
    except Exception as e:
        # Log any exceptions that occur in the worker process
        error_details = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        print(f"Error in process_voice_wrapper: {json.dumps(error_details)}")
        # Return error details
        return {
            "success": 0,
            "voice": voice if 'voice' in locals() else "unknown",
            "error": str(e)
        }


@app.route('/generate', methods=['POST'])
def generate():
    logger.info(f"\nRequest: {request}\n")

    # Print what the origin of the request is
    logger.info(f"\n\nOrigin of the request: {request.remote_addr}\n\n")

    # Mock success response
    return jsonify({
        "request_id": "req-1743174801",
        "results": {
            "donald_trump": {
                "local_path": "/outputs/1743174801_donald_trump/Mar_28_2025_Daily_Brainrot_by_Donald_Trump_final.mp4",
                "s3_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Donald_Trump_final.mp4",
                "video_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Donald_Trump_final.mp4",
                "voice": "donald_trump"
            },
            "fireship": {
                "local_path": "/outputs/1743174801_fireship/Mar_28_2025_Daily_Brainrot_by_Fireship_final.mp4",
                "s3_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Fireship_final.mp4",
                "video_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Fireship_final.mp4",
                "voice": "fireship"
            },
            "keanu_reeves": {
                "local_path": "/outputs/1743174801_keanu_reeves/Mar_28_2025_Daily_Brainrot_by_Keanu_Reeves_final.mp4",
                "s3_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Keanu_Reeves_final.mp4",
                "video_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Keanu_Reeves_final.mp4",
                "voice": "keanu_reeves"
            },
            "southpark_eric_cartman": {
                "local_path": "/outputs/1743174801_southpark_eric_cartman/Mar_28_2025_Daily_Brainrot_by_Southpark_Eric_Cartman_final.mp4",
                "s3_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Southpark_Eric_Cartman_final.mp4",
                "video_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Southpark_Eric_Cartman_final.mp4",
                "voice": "southpark_eric_cartman"
            },
            "walter_cronkite": {
                "local_path": "/outputs/1743174801_walter_cronkite/Mar_28_2025_Daily_Brainrot_by_Walter_Cronkite_final.mp4",
                "s3_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Walter_Cronkite_final.mp4",
                "video_url": "https://ai-digest-bot.s3.amazonaws.com/videos/Mar_28_2025_Daily_Brainrot_by_Walter_Cronkite_final.mp4",
                "voice": "walter_cronkite"
            }
        },
        "success": 0,
        "digestId": "ecb5b529-68e0-4656-a380-754825b1632f"
    })

    data = request.get_json()
    text = data.get('text', '')
    voices = data.get('voices', [])
    model = data.get('model', 'o3mini')
    video = data.get('video', 'minecraft')
    digest_id = data.get('digest_id')
    title = data.get('title', 'Generated Video')
    description = data.get('description', '')

    # Log the raw request data for debugging
    logger.info(f"Raw request data: {json.dumps(data)}")

    request_id = f"req-{int(time.time())}"
    logger.info(f"=== RECEIVED GENERATION REQUEST {request_id} ===")
    logger.info(f"Requested voices: {voices}")
    logger.info(f"Model: {model}, Video: {video}")
    logger.info(f"Digest ID: {digest_id}")

    if not text:
        logger.error("Missing required parameter: text")
        return jsonify({'error': 'Text is required'}), 400

    if not voices:
        logger.error("Missing required parameter: voices")
        return jsonify({'error': 'Voices are required'}), 400

    if not model:
        logger.error("Missing required parameter: model")
        return jsonify({'error': 'Model is required'}), 400

    if video not in AVAILABLE_VIDEOS:
        logger.error(
            f"Invalid video selection: {video}. Available: {list(AVAILABLE_VIDEOS.keys())}")
        return jsonify({'error': f'Invalid video. Available videos: {list(AVAILABLE_VIDEOS.keys())}'}), 400

    for voice in voices:
        if voice not in VOICES:
            logger.error(
                f"Invalid voice selection: {voice}. Available: {list(VOICES.keys())}")
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICES.keys())}'}), 400

    # Check required API keys
    missing_keys = []
    if not os.getenv('OPENAI_API_KEY'):
        missing_keys.append('OPENAI_API_KEY')
    if not os.getenv('FISH_API_KEY'):
        missing_keys.append('FISH_API_KEY')

    if missing_keys:
        error_msg = f"Missing required API keys: {', '.join(missing_keys)}. Set these environment variables."
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 400

    try:
        generated_videos = []
        overall_start_time = datetime.now()

        # Create temporary file for text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name
            logger.info(f"Created temporary file at: {temp_path}")

        # Calculate word count
        word_count = len(re.findall(r'\w+', text))
        logger.info(f"Input text contains {word_count} words")

        # Use ProcessPoolExecutor to process voices concurrently with true parallelism
        # Determine optimal number of workers based on CPU cores
        # Typically use n_cores-1 to leave one core for the OS and other tasks
        max_workers = min(len(voices), max(1, multiprocessing.cpu_count() - 1))
        logger.info(
            f"Starting parallel processing with {max_workers} processes for {len(voices)} voices")

        # For /generate route, set use_special_effects to False
        use_special_effects = False
        logger.info(f"Processing without special effects")

        # Use ProcessPoolExecutor for true parallel execution
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all voice processing jobs
            future_to_voice = {}
            for voice in voices:
                # Log the digest_id before submitting the job
                logger.info(
                    f"Submitting job for voice {voice} with digest_id: {digest_id}")

                args = (voice, text, word_count, digest_id, title,
                        description, model, video, temp_path, request_id, use_special_effects)
                future = executor.submit(process_voice_wrapper, args)
                future_to_voice[future] = voice

            # Collect results as they complete
            results = {}
            for future in concurrent.futures.as_completed(future_to_voice):
                voice = future_to_voice[future]
                try:
                    voice_result = future.result()
                    # Example: {"success": 1, "voice": "voice1", "video_url": "https://example.com/video1.mp4", "s3_url": "https://example.com/video1.mp4"}
                    results[voice] = voice_result
                    logger.info(
                        f"Successfully collected result for voice: {voice}")
                except Exception as e:
                    logger.error(
                        f"Error processing voice {voice}: {str(e)}")
                    results[voice] = {"success": 0, "error": str(e)}

        # Clean up the temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.info(f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file: {str(e)}")

        # Prepare response
        success_count = sum(1 for r in results.values()
                            if r.get('success', 0) == 1)
        logger.info(f"=== COMPLETED REQUEST {request_id} ===")
        logger.info(
            f"Total processing time: {(datetime.now() - overall_start_time).total_seconds():.2f} seconds")
        logger.info(
            f"Successfully processed: {success_count}/{len(voices)} voices")

        response = {
            "success": 1 if success_count > 0 else 0,
            "request_id": request_id,
            "results": results
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in /generate route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": 0, "error": str(e)}), 500


@app.route('/generate_special_effects', methods=['POST'])
def generate_special_effects():
    logger.info(f"\nRequest: {request}\n")

    # Print what the origin of the request is
    logger.info(f"\n\nOrigin of the request: {request.remote_addr}\n\n")

    data = request.get_json()
    text = data.get('text', '')
    voices = data.get('voices', [])
    model = data.get('model', 'o3mini')
    video = data.get('video', 'minecraft')
    digest_id = data.get('digest_id')
    title = data.get('title', 'Generated Video')
    description = data.get('description', '')

    # Log the raw request data for debugging
    logger.info(f"Raw request data: {json.dumps(data)}")

    request_id = f"req-{int(time.time())}"
    logger.info(f"=== RECEIVED GENERATION REQUEST {request_id} ===")
    logger.info(f"Requested voices: {voices}")
    logger.info(f"Model: {model}, Video: {video}")
    logger.info(f"Digest ID: {digest_id}")

    if not text:
        logger.error("Missing required parameter: text")
        return jsonify({'error': 'Text is required'}), 400

    if not voices:
        logger.error("Missing required parameter: voices")
        return jsonify({'error': 'Voices are required'}), 400

    if not model:
        logger.error("Missing required parameter: model")
        return jsonify({'error': 'Model is required'}), 400

    if video not in AVAILABLE_VIDEOS:
        logger.error(
            f"Invalid video selection: {video}. Available: {list(AVAILABLE_VIDEOS.keys())}")
        return jsonify({'error': f'Invalid video. Available videos: {list(AVAILABLE_VIDEOS.keys())}'}), 400

    for voice in voices:
        if voice not in VOICES:
            logger.error(
                f"Invalid voice selection: {voice}. Available: {list(VOICES.keys())}")
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICES.keys())}'}), 400

    # Check required API keys
    missing_keys = []
    if not os.getenv('OPENAI_API_KEY'):
        missing_keys.append('OPENAI_API_KEY')
    if not os.getenv('FISH_API_KEY'):
        missing_keys.append('FISH_API_KEY')

    if missing_keys:
        error_msg = f"Missing required API keys: {', '.join(missing_keys)}. Set these environment variables."
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 400

    try:
        generated_videos = []
        overall_start_time = datetime.now()

        # Create temporary file for text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name
            logger.info(f"Created temporary file at: {temp_path}")

        # Calculate word count
        word_count = len(re.findall(r'\w+', text))
        logger.info(f"Input text contains {word_count} words")

        # Use ProcessPoolExecutor to process voices concurrently with true parallelism
        # Determine optimal number of workers based on CPU cores
        # Typically use n_cores-1 to leave one core for the OS and other tasks
        max_workers = min(len(voices), max(1, multiprocessing.cpu_count() - 1))
        logger.info(
            f"Starting parallel processing with {max_workers} processes for {len(voices)} voices")

        # For /generate_special_effects route, set use_special_effects to True
        use_special_effects = True
        logger.info(f"Processing with special effects enabled")

        # Use ProcessPoolExecutor for true parallel execution
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all voice processing jobs
            future_to_voice = {}
            for voice in voices:
                # Log the digest_id before submitting the job
                logger.info(
                    f"Submitting job for voice {voice} with digest_id: {digest_id}")

                args = (voice, text, word_count, digest_id, title,
                        description, model, video, temp_path, request_id, use_special_effects)
                future = executor.submit(process_voice_wrapper, args)
                future_to_voice[future] = voice

            # Collect results as they complete
            results = {}
            for future in concurrent.futures.as_completed(future_to_voice):
                voice = future_to_voice[future]
                try:
                    voice_result = future.result()
                    # Example: {"success": 1, "voice": "voice1", "video_url": "https://example.com/video1.mp4", "s3_url": "https://example.com/video1.mp4"}
                    results[voice] = voice_result
                    logger.info(
                        f"Successfully collected result for voice: {voice}")
                except Exception as e:
                    logger.error(
                        f"Error processing voice {voice}: {str(e)}")
                    results[voice] = {"success": 0, "error": str(e)}

        # Clean up the temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.info(f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file: {str(e)}")

        # Prepare response
        success_count = sum(1 for r in results.values()
                            if r.get('success', 0) == 1)
        logger.info(f"=== COMPLETED REQUEST {request_id} ===")
        logger.info(
            f"Total processing time: {(datetime.now() - overall_start_time).total_seconds():.2f} seconds")
        logger.info(
            f"Successfully processed: {success_count}/{len(voices)} voices")

        response = {
            "success": 1 if success_count > 0 else 0,
            "request_id": request_id,
            "results": results
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in /generate route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": 0, "error": str(e)}), 500


def process_single_voice(voice, digest_id, digest, content, temp_path, model, video, db):
    """Process a single voice for a digest"""
    try:
        timestamp = int(time.time())

        # Create video record
        video_data = {
            "digest_id": digest_id,
            "title": f"Digest {digest.get('date', 'Unknown')} - {voice.replace('_', ' ').title()}",
            "description": digest.get('summary', ''),
            "voice": voice,
            "background_video": video,
            "status": "processing",
            "word_count": len(re.findall(r'\w+', content)),
            "s3_url": "",
            "metadata": {
                "model": model,
                "start_time": datetime.now().isoformat(),
                "voice": voice,
                "content_preview": content[:500] + ("..." if len(content) > 500 else "")
            }
        }

        logger.info(f"Creating video record with voice: {voice}")
        result = db.insert_video(video_data)
        video_id = result[0]["id"]

        # Generate video
        result = main(temp_path, llm=False, voice=voice,
                      model=model, video_path=AVAILABLE_VIDEOS[video],
                      s3_bucket=S3_BUCKET, timestamp=timestamp,
                      api_key=os.getenv('OPENAI_API_KEY'))

        video_path, s3_url = result if isinstance(
            result, tuple) else (result, None)

        if os.path.exists(video_path):
            # Update video record
            db.update_video_status(video_id, "completed", {
                "end_time": datetime.now().isoformat()
            })

            # Update s3_url if available
            if s3_url:
                db.supabase.table("videos").update(
                    {"s3_url": s3_url}).eq("id", video_id).execute()
            elif os.path.exists(video_path):
                db.supabase.table("videos").update(
                    {"s3_url": video_path}).eq("id", video_id).execute()

            return {
                'voice': voice,
                'video_id': video_id,
                'status': 'completed',
                's3_url': s3_url if s3_url else video_path
            }
        else:
            db.update_video_status(video_id, "failed", {
                "error": "Video generation failed",
                "end_time": datetime.now().isoformat()
            })
            return {
                'voice': voice,
                'video_id': video_id,
                'status': 'failed'
            }

    except Exception as e:
        logger.error(f"Error processing voice {voice}: {str(e)}")
        if 'video_id' in locals():
            try:
                db.update_video_status(video_id, "failed", {
                    "error": str(e),
                    "end_time": datetime.now().isoformat()
                })
            except Exception as db_error:
                logger.error(f"Error updating video status: {str(db_error)}")

        return {
            'voice': voice,
            'status': 'failed',
            'error': str(e)
        }


@app.route('/final/<path:filename>')
def serve_video(filename):
    return send_from_directory('final', filename)


@app.route('/available_voices', methods=['GET'])
def get_available_voices():
    voices = VOICE_IDS.keys()
    return jsonify(voices)


@app.route('/available_models', methods=['GET'])
def get_available_models():
    models = MODELS.keys()
    return jsonify(models)


@app.route('/available_videos', methods=['GET'])
def get_available_videos():
    """Return list of available background videos"""
    return jsonify(list(AVAILABLE_VIDEOS.keys()))


@app.route('/status', methods=['GET'])
def get_status():
    """Get system status including Supabase connection"""
    status = {
        "server": "running",
        "s3_enabled": bool(S3_BUCKET),
        "supabase_enabled": SUPABASE_ENABLED,
        "available_voices": list(VOICE_IDS.keys()),
        "available_models": list(MODELS.keys()),
        "available_videos": list(AVAILABLE_VIDEOS.keys())
    }

    # Add Supabase stats if enabled
    if SUPABASE_ENABLED:
        try:
            pending_videos = db.get_pending_videos()
            status["pending_videos"] = len(pending_videos)
        except Exception as e:
            status["supabase_error"] = str(e)

    return jsonify(status)


@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'supabase_enabled': SUPABASE_ENABLED
    }), 200


if __name__ == "__main__":
    print("\n=== Starting Server ===")
    print("Checking required files and directories...")
    missing = check_required_files()
    if missing:
        print("\nWarnings:")
        for msg in missing:
            print(f"- {msg}")
        print("\nNote: Required API keys must be set for all functionality to work.")
    else:
        print("All required files, directories, and environment variables present")

    print(
        f"Supabase integration: {'Enabled' if SUPABASE_ENABLED else 'Disabled'}")
    print(f"S3 integration: {'Enabled' if S3_BUCKET else 'Disabled'}")

    print("\nStarting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5500)
