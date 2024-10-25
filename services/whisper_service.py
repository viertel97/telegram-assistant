import os
import time
from datetime import datetime, timedelta

from gradio_client import handle_file, Client
from pydub import AudioSegment
from quarter_lib.logging import setup_logging
from telegram import Update

from helper.telegram_helper import retry_on_error

logger = setup_logging(__file__)


def millis_to_time_format(ms):
    hours, remainder = divmod(ms // 1000, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


async def split_and_process_audio(audio_file, seconds: float, overlap_seconds: float, filename: str,
                                  segment_counter: int, client: Client,
async def split_and_process_audio(audio_file, seconds: float, overlap_seconds: float, call_date: datetime, client: Client,
                                  update: Update):
    audio = AudioSegment.from_wav(audio_file.name)
    segment_length = int(seconds * 1000)  # Convert seconds to milliseconds
    overlap_length = int(overlap_seconds * 1000)  # Convert overlap seconds to milliseconds
    transcription = ""
    to_delete = []
    if not segment_counter:
        segment_counter = 1  # Counter for naming segments

    # Start the segment loop with overlap in both directions
    start = (segment_counter - 1) * segment_length
    while start < len(audio):
        start_step = start - overlap_length
        if start_step < 0:
            start_step = 0
        end = min(start + segment_length + overlap_length, len(audio))  # Ensure not to exceed file length
        segment = audio[start_step: end]

        # Adjusted segment naming to be "Seg1:", "Seg2:", etc.
        segment_name = f"segment_{segment_counter}.wav"
        segment.export(segment_name, format="wav")

        # Get start and end time in (hours:minutes:seconds)
        start_time = millis_to_time_format(start_step)
        end_time = millis_to_time_format(end)

        start_datetime = call_date + timedelta(milliseconds=start_step)
        end_datetime = call_date + timedelta(milliseconds=end)

        # Update caption with the desired format
        caption_text = f"Start: {start_time} ({start_datetime.strftime('%Y-%m-%d %H:%M:%S')})\n" \
                       f"End: {end_time} ({end_datetime.strftime('%Y-%m-%d %H:%M:%S')})"

        await retry_on_error(
            update.message.reply_audio,
            retry=5,
            wait=0.1,
            audio=open(segment_name, "rb"),
            disable_notification=True,
            caption=caption_text
        )

        transcribed_text = transcribe_segment(segment_name, client)

        if transcribed_text is not None:
            logger.info(f"Transcription for {segment_name}: {transcribed_text}")
            await retry_on_error(update.message.reply_text, retry=5, wait=0.1,
                                 text=f"Transcription for '{segment_name}': \n{transcribed_text}",
                                 disable_notification=True)
            transcription += transcribed_text + " "
        else:
            await retry_on_error(update.message.reply_text, retry=5, wait=0.1,
                                 text=f"Error transcribing {segment_name}.",
                                 disable_notification=True)

        to_delete.append(segment_name)

        start += segment_length
        segment_counter += 1

    for file in to_delete:
        try:
            os.remove(file)
        except Exception as e:
            logger.error(f"Error deleting file: {e}")

    return transcription.strip()


def transcribe_segment(segment_file, client: Client):
    counter = 0
    try:
        job = client.submit(
            handle_file(segment_file),
            model="bofenghuang/whisper-large-v2-cv11-german-ct2",
            task="transcribe",
            temperature=0,
            stream=True,
            api_name="/predict",
        )
        # Add counter to log only every 5 seconds
        while not job.done():
            time.sleep(1)
            counter += 1
            if counter % 5 == 0:
                logger.info(f"Status: {job.status()}")
        response = job.result()
        del job
        return response
    except Exception as e:
        logger.error(f"Error transcribing segment: {e}")
        return ""


async def transcribe(audio_file, call_info: dict, start_at_segment: int, update: Update):
    try:
        client = Client("http://faster-whisper-server.default.svc.cluster.local:8000")
    except Exception:
        client = Client("http://localhost:8000")

    segment_length = 60  # 1-minute segment
    overlap_seconds = 5  # Define overlap (e.g., 5 seconds)

    max_retries = 5
    final_transcription = ""  # Collect all transcriptions here

    retry_count = 0

    while retry_count < max_retries:
        # Process and accumulate transcription for all segments at the current length
        transcription = await split_and_process_audio(audio_file, segment_length, overlap_seconds, call_info['date'],
                                                      start_at_segment, client,
                                                      update)

        # If transcription is successful (non-empty), accumulate the result
        if transcription:
            final_transcription += transcription + " "
            retry_count = 0  # Reset retry counter on success
            break  # Exit retry loop and move to the next segment

        # Increment retry count if there was an issue
        retry_count += 1
        await retry_on_error(update.message.reply_text, retry=5, wait=0.1,
                             text=f"Retry {retry_count}/{max_retries} for {segment_length}-second segments...",
                             disable_notification=True)