import logging
import httpx
from soniox import SonioxClient
from soniox.types import CreateTranscriptionConfig
from soniox.utils import render_tokens

logger = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, soniox_api_key: str):
        self._client = SonioxClient(api_key=soniox_api_key)

    def transcribe_voice(self, telegram_token: str, file_id: str) -> str | None:
        """Download a Telegram voice file and transcribe it via Soniox."""
        # Get file path from Telegram
        with httpx.Client() as http:
            resp = http.get(f"https://api.telegram.org/bot{telegram_token}/getFile",
                            params={"file_id": file_id})
            file_path = resp.json()["result"]["file_path"]

            # Download the voice file
            resp = http.get(f"https://api.telegram.org/file/bot{telegram_token}/{file_path}")
            audio_bytes = resp.content

        logger.info("Downloaded voice file: %s (%d bytes)", file_path, len(audio_bytes))

        # Upload to Soniox
        uploaded = self._client.files.upload(audio_bytes)
        logger.info("Uploaded to Soniox: file_id=%s", uploaded.id)

        try:
            # Create transcription
            transcription = self._client.transcriptions.create(
                config=CreateTranscriptionConfig(
                    model="stt-async-v4",
                    language_hints=["es", "en"],
                ),
                file_id=uploaded.id,
            )

            # Wait for completion
            self._client.transcriptions.wait(transcription.id)

            # Get result
            result = self._client.transcriptions.get_transcript(transcription.id)
            text = render_tokens(result.tokens, []).strip()
            logger.info("Transcription complete: %r", text[:120])

            # Cleanup
            self._client.transcriptions.delete(transcription.id)

            return text if text else None
        finally:
            self._client.files.delete(uploaded.id)
