import subprocess
import os
import edge_tts


### Use Microsoft Edge TTS for better voice quality
async def audio(text_file_path, file_path="audio/output.wav", speaker_wav="assets/default.mp3", language="en-us"):
    # Read the text from the file
    with open(text_file_path, 'r', encoding='utf-8') as file:
        text = file.read().strip()
    
    # Voice options:
    # en-US-AriaNeural - Female professional
    # en-US-GuyNeural - Male professional
    # en-US-JennyNeural - Female casual
    # en-US-SteffanNeural - Male casual
    # en-GB-SoniaNeural - British female
    # en-AU-NatashaNeural - Australian female
    voice = "en-US-JennyNeural"
    
    # Use Edge TTS
    mp3_path = "audio/output.mp3"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)
    
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
def audio_wrapper(text_file_path, file_path="audio/output.wav", speaker_wav="assets/default.mp3", language="en-us"):
    import asyncio
    asyncio.run(audio(text_file_path, file_path, speaker_wav, language))


## Converting audio to 16khz, 16 bit and mono so that we can represent them during force alignment
def convert_audio(input_path, output_path):
    command = [
        'ffmpeg',
        '-i', input_path,  # Input file
        '-ac', '1',  # Set number of audio channels to 1 (mono)
        '-ar', '16000',  # Set audio sampling rate to 16kHz
        '-sample_fmt', 's16',  # Set sample format to 16-bit
        '-y',  # Overwrite output file if it exists
        output_path  # Output file
    ]
    subprocess.run(command, check=True)
    print("AUDIO CONVERSION DONE!")

