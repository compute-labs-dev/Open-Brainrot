import os
import subprocess
from dotenv import load_dotenv
import httpx
import ormsgpack
from pydantic import BaseModel
from typing import Dict, Optional, Literal
import logging
import asyncio
import time
import random
from contextlib import asynccontextmanager

# Configure module-level logger
logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str
    reference_id: Optional[str] = None
    chunk_length: int = 200
    normalize: bool = True
    format: Literal["wav", "pcm", "mp3", "opus"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 192
    latency: Literal["normal", "balanced"] = "normal"
    model: Literal["speech-1.6"] = "speech-1.6"  # Required model parameter
    prosody: Dict[str, float] = {
        "speed": 0.9,  # Slowed down for more natural pacing
    }


VOICE_IDS = {
    "donald_trump": "5196af35f6ff4a0dbf541793fc9f2157",
    "elon_musk": "03397b4c4be74759b72533b663fbd001",
    "cristiano_ronaldo": "86304d8fa1734bd89291acf4060d8a5e",
    "joe_biden": "9b42223616644104a4534968cd612053",
    "barack_obama": "4ce7e917cedd4bc2bb2e6ff3a46acaa1",
    "robert_downey_jr": "256e1a3007a74904a91d132d1e9bf0aa",
    "andrew_tate": "a4d46c9bdf1f40f9a6354f1423d53cc3",
    "rick_sanchez": "d2e75a3e3fd6419893057c02a375a113",
    "morty_smith": "3d445d095ba04681bcba7177faedf55a",
    "walter_cronkite": "d204ec5aad8d4ee080c6a5341e84bdbf",
    "portals_glados": "ee885900b0874d12b1c3439d1e56cc95",
    "southpark_eric_cartman": "b4f55643a15944e499defe42964d2ebf",
    "kermit_the_frog": "e4ab98de928a4791a8613f102caae78a",
    "yelling_kermit": "e4ab98de928a4791a8613f102caae78a",
    "keanu_reeves": "c69fea85f15f4c809be8f52ddbb09709",
    "fireship": "4dbf597a6a134c94b53d2830d67aabd8"
}


VOICE_SPEEDS = {
    "donald_trump": 1.0,
    "elon_musk": 1.25,
    "andrew_tate": 1.25,
    "barack_obama": 1.25,
    "rick_sanchez": 1.25,
    "morty_smith": 1.25,
    "walter_cronkite": 1.25,
    "portals_glados": 1.25,
    "southpark_eric_cartman": 1.25,
    "kermit_the_frog": 1.25,
    "yelling_kermit": 1.25,
    "keanu_reeves": 1.25,
    "fireship": 1.3,
    "default": 0.9
}


# Context manager for httpx client to ensure proper cleanup
@asynccontextmanager
async def get_httpx_client(timeout=60.0):
    client = httpx.AsyncClient(timeout=timeout)
    try:
        yield client
    finally:
        await client.aclose()


async def generate_voice(text, voice_id, output_path="audio/output.mp3", max_retries=3, timeout=60.0):
    """Generate audio using Fish Audio API with special effects support"""
    load_dotenv()
    api_key = os.getenv("FISH_API_KEY")

    if not api_key:
        raise ValueError("FISH_API_KEY not found in environment variables")

    # Get the voice name from voice_id for logging
    voice_name = next((k for k, v in VOICE_IDS.items()
                      if v == voice_id), "unknown_voice")

    # Add context to logs
    log_prefix = f"[Voice:{voice_name}]"
    logger.info(
        f"{log_prefix} Generating voice audio for output: {output_path}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    retries = 0
    last_error = None

    while retries < max_retries:
        try:
            # Get voice-specific speed or use default
            speed = VOICE_SPEEDS.get(voice_name, VOICE_SPEEDS["default"])
            logger.info(f"{log_prefix} Using voice speed: {speed}")

            request = TTSRequest(
                text=text,
                reference_id=voice_id,
                chunk_length=200,
                mp3_bitrate=192,
                # normalize=True,
                model="speech-1.6",  # Required model parameter
                prosody={
                    "speed": speed,
                }
            )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "model": "speech-1.6"  # Also include in headers
            }

            logger.info(
                f"{log_prefix} Making API request to Fish Audio (attempt {retries+1}/{max_retries})")
            # Use context manager to ensure client is properly closed
            async with get_httpx_client(timeout=timeout) as client:
                start_time = time.time()
                try:
                    async with client.stream(
                        "POST",
                        "https://api.fish.audio/v1/tts",
                        json=request.model_dump(),
                        headers=headers,
                        timeout=timeout
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(
                                f"{log_prefix} Fish Audio API Error: {response.status_code}")
                            logger.error(
                                f"{log_prefix} Error details: {error_text.decode()}")
                            raise Exception(
                                f"Fish Audio API error: {response.status_code}")

                        logger.info(
                            f"{log_prefix} Received successful response, writing to file")
                        with open(output_path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)

                    duration = time.time() - start_time
                    logger.info(
                        f"{log_prefix} API request completed in {duration:.2f} seconds")
                    return output_path
                except httpx.TimeoutException:
                    logger.warning(
                        f"{log_prefix} Request timed out after {timeout} seconds")
                    raise

        except Exception as e:
            last_error = e
            retries += 1
            logger.error(f"{log_prefix} Fish Audio API Error: {str(e)}")

            if retries < max_retries:
                # Exponential backoff with jitter
                wait_time = (2 ** retries) + random.uniform(0, 1)
                logger.info(
                    f"{log_prefix} Retrying in {wait_time:.2f} seconds (attempt {retries+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"{log_prefix} All {max_retries} attempts failed")
                break

    # If we got here, all retries failed
    raise last_error or Exception(
        "Failed to generate voice after multiple attempts")


async def audio(text_file_path, file_path="audio/output.wav", voice="donald_trump"):
    """
    Generate audio from text using Fish Audio voices

    Args:
        text_file_path: Path to text file to convert
        file_path: Output WAV file path
        voice: Voice key from VOICE_IDS dict
    """
    # Add context to logs
    log_prefix = f"[Voice:{voice}]"
    logger.info(
        f"{log_prefix} Starting audio generation from text file: {text_file_path}")

    # Read the text from file
    try:
        with open(text_file_path, 'r', encoding='utf-8') as file:
            text = file.read().strip()
        logger.info(f"{log_prefix} Read {len(text)} characters from text file")
    except Exception as e:
        logger.error(f"{log_prefix} Failed to read text file: {str(e)}")
        raise

    # Get voice ID
    voice_id = VOICE_IDS.get(voice)
    if not voice_id:
        error_msg = f"Invalid voice '{voice}'. Valid options are: {list(VOICE_IDS.keys())}"
        logger.error(f"{log_prefix} {error_msg}")
        raise ValueError(error_msg)

    # Create voice-specific intermediate MP3 path (use same directory as the output file)
    output_dir = os.path.dirname(file_path)
    mp3_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_{voice}_temp.mp3"
    mp3_path = os.path.join(output_dir, mp3_filename)

    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"{log_prefix} Using temporary MP3 path: {mp3_path}")

    # Generate MP3 with Fish Audio
    try:
        await generate_voice(text, voice_id, mp3_path)
        logger.info(f"{log_prefix} Successfully generated MP3 voice audio")
    except Exception as e:
        logger.error(f"{log_prefix} Failed to generate voice audio: {str(e)}")
        raise

    # Convert MP3 to WAV using ffmpeg
    try:
        logger.info(f"{log_prefix} Converting MP3 to WAV format: {file_path}")
        command = [
            'ffmpeg',
            '-i', mp3_path,
            '-y',  # Overwrite output file if it exists
            file_path
        ]
        # Capture ffmpeg output for logging
        result = subprocess.run(command, check=True,
                                capture_output=True, text=True)
        logger.info(f"{log_prefix} TTS conversion complete")

        if result.stderr:
            logger.debug(f"{log_prefix} ffmpeg output: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"{log_prefix} ffmpeg error: {e.stderr}")
        raise
    except Exception as e:
        logger.error(
            f"{log_prefix} Error during MP3 to WAV conversion: {str(e)}")
        raise

    # Clean up the temporary MP3 file
    try:
        os.remove(mp3_path)
        logger.info(f"{log_prefix} Removed temporary MP3 file: {mp3_path}")
    except Exception as e:
        logger.warning(
            f"{log_prefix} Failed to remove temporary MP3 file: {str(e)}")

# Non-async wrapper for compatibility


def audio_wrapper(text_file_path, file_path="audio/output.wav", voice="donald_trump"):
    """Synchronous wrapper for the async audio function"""
    # Add context to logs
    log_prefix = f"[Voice:{voice}]"
    logger.info(
        f"{log_prefix} Starting audio_wrapper for file: {text_file_path}")

    try:
        import asyncio
        # Create a new event loop for this process to avoid conflicts in multiprocessing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            audio(text_file_path, file_path, voice))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"{log_prefix} Error in audio_wrapper: {str(e)}")
        raise


def convert_audio(input_path, output_path):
    """Convert audio to 16kHz, 16-bit mono for force alignment"""
    # Extract voice name from the path if possible for better logging
    filename = os.path.basename(input_path)
    voice_match = None
    for voice_name in VOICE_IDS.keys():
        if voice_name in filename:
            voice_match = voice_name
            break

    log_prefix = f"[Voice:{voice_match or 'unknown'}]"
    logger.info(
        f"{log_prefix} Converting audio to 16kHz mono: {input_path} -> {output_path}")

    try:
        command = [
            'ffmpeg',
            '-i', input_path,
            '-ac', '1',  # Set to mono
            '-ar', '16000',  # Set to 16kHz
            '-sample_fmt', 's16',  # Set to 16-bit
            '-y',  # Overwrite output file
            output_path
        ]

        # Capture output for better logging
        result = subprocess.run(command, check=True,
                                capture_output=True, text=True)

        if result.stderr:
            logger.debug(f"{log_prefix} ffmpeg output: {result.stderr}")

        logger.info(f"{log_prefix} AUDIO CONVERSION DONE!")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_prefix} Error during audio conversion: {e.stderr}")
        raise
    except Exception as e:
        logger.error(
            f"{log_prefix} Unexpected error during audio conversion: {str(e)}")
        raise
