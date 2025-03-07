import os
import subprocess
from dotenv import load_dotenv
import httpx
import ormsgpack
from pydantic import BaseModel
from typing import Dict, Optional, Literal


class TTSRequest(BaseModel):
    text: str
    reference_id: Optional[str] = None
    chunk_length: int = 200
    normalize: bool = True
    format: Literal["wav", "pcm", "mp3", "opus"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 192
    latency: Literal["normal", "balanced"] = "normal"
    model: Literal["speech-1.6"] = "speech-1.6"
    prosody: Dict[str, float] = {
        "speed": 1.1,
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
    "keanu_reeves": "c69fea85f15f4c809be8f52ddbb09709"
}


VOICE_SPEEDS = {
    "walter_cronkite": 1.1,
    "default": 1.2
}


async def generate_voice(text, voice_id, output_path="audio/output.mp3"):
    """Generate audio using Fish Audio API with special effects support"""
    load_dotenv()
    api_key = os.getenv("FISH_API_KEY")

    if not api_key:
        raise ValueError("FISH_API_KEY not found in environment variables")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # Get the voice name from voice_id by finding the key in VOICE_IDS
        voice_name = next(
            (k for k, v in VOICE_IDS.items() if v == voice_id), None)
        # Get voice-specific speed or use default
        speed = VOICE_SPEEDS.get(voice_name, VOICE_SPEEDS["default"])

        request = TTSRequest(
            text=text,
            reference_id=voice_id,
            chunk_length=200,
            mp3_bitrate=192,
            # normalize=True,
            model="speech-1.6",
            prosody={
                "speed": speed,
            }
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": "speech-1.6"
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.fish.audio/v1/tts",
                json=request.model_dump(),
                headers=headers,
                timeout=None
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Fish Audio API Error: {response.status_code}")
                    print(f"Error details: {error_text.decode()}")
                    raise Exception(
                        f"Fish Audio API error: {response.status_code}")

                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

        return output_path

    except Exception as e:
        print(f"Fish Audio API Error: {str(e)}")
        raise


async def audio(text_file_path, file_path="audio/output.wav", voice="donald_trump"):
    """
    Generate audio from text using Fish Audio voices

    Args:
        text_file_path: Path to text file to convert
        file_path: Output WAV file path
        voice: Voice key from VOICE_IDS dict
    """
    # Read the text from file
    with open(text_file_path, 'r', encoding='utf-8') as file:
        text = file.read().strip()

    # Get voice ID
    voice_id = VOICE_IDS.get(voice)
    if not voice_id:
        raise ValueError(
            f"Invalid voice '{voice}'. Valid options are: {list(VOICE_IDS.keys())}")

    # Generate MP3 with Fish Audio
    mp3_path = "audio/output.mp3"
    await generate_voice(text, voice_id, mp3_path)

    # Convert MP3 to WAV using ffmpeg
    command = [
        'ffmpeg',
        '-i', mp3_path,
        '-y',  # Overwrite output file if it exists
        file_path
    ]
    subprocess.run(command, check=True)
    print("TTS conversion complete!")

# Non-async wrapper for compatibility


def audio_wrapper(text_file_path, file_path="audio/output.wav", voice="donald_trump"):
    import asyncio
    asyncio.run(audio(text_file_path, file_path, voice))


def convert_audio(input_path, output_path):
    """Convert audio to 16kHz, 16-bit mono for force alignment"""
    command = [
        'ffmpeg',
        '-i', input_path,
        '-ac', '1',  # Set to mono
        '-ar', '16000',  # Set to 16kHz
        '-sample_fmt', 's16',  # Set to 16-bit
        '-y',  # Overwrite output file
        output_path
    ]
    subprocess.run(command, check=True)
    print("AUDIO CONVERSION DONE!")
