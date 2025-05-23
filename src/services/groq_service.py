import os
import wave

from groq import Groq
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.telegram_helper import retry_on_error

logger = setup_logging(__file__)

GROQ_API_KEY = get_secrets(["groq/api_key"])

CLIENT = Groq(api_key=GROQ_API_KEY)
MODEL = "whisper-large-v3"


def split_wav_by_size(input_file, max_chunk_size_mb=20):
	files = []
	max_chunk_size_bytes = max_chunk_size_mb * 1024 * 1024

	# Open the original WAV file
	with wave.open(input_file, "rb") as wav:
		params = wav.getparams()  # Get file parameters
		frame_rate = params.framerate
		n_channels = params.nchannels
		sample_width = params.sampwidth

		frames_per_chunk = max_chunk_size_bytes // sample_width // n_channels

		chunk_index = 1
		while True:
			frames = wav.readframes(frames_per_chunk)
			if not frames:
				break

			output_file = f"{os.path.splitext(input_file)[0]}_chunk{chunk_index}.wav"
			with wave.open(output_file, "wb") as chunk_wav:
				chunk_wav.setparams(params)  # Copy original params
				chunk_wav.writeframes(frames)

			logger.info(f"Saved chunk: {output_file}")
			files.append(output_file)
			chunk_index += 1
	return files


def audio_to_text(filepath, prompt=None):
	with open(filepath, "rb") as file:
		params = {
			"file": (filepath, file.read()),
			"model": MODEL,
		}
		if prompt is not None:
			params["prompt"] = prompt  # Only add if set

		translation = CLIENT.audio.transcriptions.create(**params)

	return translation.text


async def transcribe_groq(audio_file, file_function, text_function, prompt=None, **kwargs):
	transcription_list = []
	chunk_files = split_wav_by_size(audio_file)
	for chunk_file in chunk_files:
		logger.info(f"Transcribing chunk: {chunk_file}")
		transcription = audio_to_text(chunk_file, prompt)
		logger.info(f"Transcription: {transcription}")
		await retry_on_error(
			file_function,
			retry=5,
			wait=0.1,
			caption=f"'{chunk_file}'",
			disable_notification=True,
			document=open(chunk_file, "rb"),
			**kwargs,
		)
		await retry_on_error(
			text_function,
			retry=5,
			wait=0.1,
			text=f"Transcription for '{chunk_file}':\n\n{transcription}",
			disable_notification=True,
			**kwargs,
		)
		os.remove(chunk_file)
		transcription_list.append(transcription)
	return transcription_list
