from pydub import AudioSegment
import os
from gradio_client import handle_file, Client
from telegram import Update

client = Client("http://localhost:8000")


# Function to split the audio into 10-second segments
def split_audio(audio_file):
    audio = AudioSegment.from_wav(audio_file.name)
    segment_length = 15 * 1000  # 10 seconds in milliseconds
    segments = []

    for i in range(0, len(audio), segment_length):
        segment = audio[i:i + segment_length]
        segment_name = f"segment_{i // segment_length}.wav"
        segment.export(segment_name, format="wav")
        segments.append(segment_name)

    return segments


# Function to call the transcription API for each audio segment
def transcribe_segment(segment_file, update:Update):
    try:
        response = client.predict(handle_file(segment_file), model="bofenghuang/whisper-large-v2-cv11-german-ct2",
                                  task="transcribe",
                                  temperature=0,
                                  stream=True,
                                  api_name="/predict"
                                  )
    except Exception:
        print("Error")
        response = ""
    return response


# Function to handle the entire transcription process
def transcribe(audio_file, update):
    segments = split_audio(audio_file)  # Split into 10s segments
    transcription = ""

    # Transcribe each segment
    for segment in segments:
        update.message.reply_text(f"Transcribing {segment}...")
        transcription += transcribe_segment(segment) + " "

        # Clean up segment files
        os.remove(segment)

    return transcription.strip()