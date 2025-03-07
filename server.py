from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS  # Add CORS support
from audio import VOICE_IDS
from brainrot_generator import MODELS, VOICE_STYLES
from main import main
import os
import tempfile
import traceback  # Add this for better error tracking
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load environment variables
load_dotenv()

# Get S3 configuration from environment variables
S3_BUCKET = os.getenv('S3_BUCKET')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Available background videos
AVAILABLE_VIDEOS = {
    "minecraft": "assets/minecraft.mp4",
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
        'assets/minecraft.mp4': 'Minecraft background video file',
        'assets/subway.mp4': 'Subway background video file',
        'assets/default.mp3': 'Default audio file'
    }

    required_dirs = {
        'final': 'Output directory',
        'audio': 'Audio directory',
        'texts': 'Text directory',
        'outputs': 'Processing directory'
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

    return missing


@app.route('/')
def index():
    # Check required files on startup
    missing = check_required_files()
    if missing:
        return jsonify({
            "status": "Server running with warnings",
            "warnings": missing,
            "s3_enabled": bool(S3_BUCKET)
        }), 200
    return jsonify({
        "status": "Server is running",
        "s3_enabled": bool(S3_BUCKET)
    }), 200


@app.route('/generate_multiple', methods=['POST'])
def generate_multiple():
    # input: {
    #     "text": "text",
    #     "voices": ["voice1", "voice2", "voice3"],
    #     "model": "o3mini",
    #     "video": "minecraft"
    # }
    data = request.get_json()
    text = data.get('text', '')
    voices = data.get('voices', [])
    model = data.get('model', 'o3mini')
    video = data.get('video', 'minecraft')

    if not text:
        return jsonify({'error': 'Text is required'}), 400

    if not voices:
        return jsonify({'error': 'Voices are required'}), 400

    if not model:
        return jsonify({'error': 'Model is required'}), 400

    if video not in AVAILABLE_VIDEOS:
        return jsonify({'error': f'Invalid video. Available videos: {list(AVAILABLE_VIDEOS.keys())}'}), 400

    for voice in voices:
        if voice not in VOICE_STYLES:
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICE_STYLES.keys())}'}), 400

    try:
        generated_videos = []

        # Create temporary file for text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name
            print(f"Created temporary file at: {temp_path}")

        # Generate video for each voice
        for voice in voices:
            print(f"\nStarting video generation for voice: {voice}")
            result = main(temp_path, llm=False, voice=voice,
                          model=model, video_path=AVAILABLE_VIDEOS[video])

            # Unpack the result tuple
            video_path, s3_url = result if isinstance(
                result, tuple) else (result, None)
            print(f"Video generation completed with result: {video_path}")

            if os.path.exists(video_path):
                relative_path = os.path.relpath(video_path, os.getcwd())
                video_info = {
                    'voice': voice,
                    'video_url': f'/{relative_path}'
                }
                if s3_url:
                    video_info['s3_url'] = s3_url
                generated_videos.append(video_info)
            else:
                print(f"Video generation failed for voice: {voice}")

        # Clean up temporary file
        os.unlink(temp_path)
        print(f"Cleaned up temporary file: {temp_path}")

        if generated_videos:
            return jsonify({
                'status': 'success',
                'videos': generated_videos
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No videos were successfully generated'
            }), 500

    except Exception as e:
        print(f"Error in generate_multiple: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Video generation failed: {str(e)}'
        }), 500


@app.route('/generate', methods=['POST'])
def generate():
    print("Received request at /generate")
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    text = data.get('text', '')
    voice = data.get('voice', 'donald_trump')
    model = data.get('model', 'claude')
    video = data.get('video', 'minecraft')

    if video not in AVAILABLE_VIDEOS:
        return jsonify({'error': f'Invalid video. Available videos: {list(AVAILABLE_VIDEOS.keys())}'}), 400

    try:
        # Create temporary file for text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name
            print(f"Created temporary file at: {temp_path}")

        # Generate video
        print("\nStarting video generation...")
        video_path = main(temp_path, llm=False, voice=voice,
                          model=model, video_path=AVAILABLE_VIDEOS[video])
        print(f"Video generation completed with result: {video_path}")

        # Clean up temporary file
        os.unlink(temp_path)
        print(f"Cleaned up temporary file: {temp_path}")

        # Check if video was generated
        print(f"Looking for generated video at: {video_path}")
        if os.path.exists(video_path):
            print("Video generation successful")
            relative_path = os.path.relpath(video_path, os.getcwd())
            return jsonify({'video_url': f'/{relative_path}'})
        else:
            print("Video generation failed")
            return jsonify({'error': 'Video generation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_from_text', methods=['POST'])
def generate_from_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', 'donald_trump')
        model = data.get('model', 'claude')
        video = data.get('video', 'minecraft')

        if not text:
            return jsonify({'error': 'Text is required'}), 400

        if voice not in VOICE_STYLES:
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICE_STYLES.keys())}'}), 400

        if video not in AVAILABLE_VIDEOS:
            return jsonify({'error': f'Invalid video. Available videos: {list(AVAILABLE_VIDEOS.keys())}'}), 400

        # Create temporary file for text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name
            print(f"Created temporary file at: {temp_path}")

        print("\nStarting video generation...")
        video_path, s3_url = main(
            temp_path, llm=False, voice=voice, model=model, s3_bucket=S3_BUCKET,
            video_path=AVAILABLE_VIDEOS[video]
        )
        print(f"Video generation completed with result: {video_path}")

        # Clean up temporary file
        os.unlink(temp_path)
        print(f"Cleaned up temporary file: {temp_path}")

        # Check if video was generated
        print(f"Looking for generated video at: {video_path}")
        if os.path.exists(video_path):
            print("Video generation successful")
            response = {
                'status': 'success',
                'local_video_url': f"/{os.path.relpath(video_path, os.getcwd())}"
            }
            if s3_url:
                response['s3_url'] = s3_url
            return jsonify(response)
        else:
            return jsonify({
                'status': 'error',
                'message': 'Video generation failed - file not found'
            }), 500

    except Exception as e:
        print(f"Error in generate_from_text: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Video generation failed: {str(e)}'
        }), 500


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


if __name__ == "__main__":
    print("\n=== Starting Server ===")
    print("Checking required files and directories...")
    missing = check_required_files()
    if missing:
        print("\nWarnings:")
        for msg in missing:
            print(f"- {msg}")
    else:
        print("All required files and directories present")

    print("\nStarting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5500)
