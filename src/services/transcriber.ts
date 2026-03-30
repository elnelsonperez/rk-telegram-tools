import { SonioxNodeClient } from "@soniox/node";
import { createLogger } from "../logger.js";

const log = createLogger("transcriber");

/**
 * Transcribe a Telegram voice note using the Soniox async STT API.
 *
 * Flow:
 *  1. Resolve the file path via Telegram's getFile endpoint.
 *  2. Download the audio bytes from Telegram's file server.
 *  3. Upload to Soniox, transcribe with Spanish/English hints, and wait.
 *  4. Return the transcript text (or null when empty / on failure).
 */
export async function transcribeVoice(
  botToken: string,
  sonioxApiKey: string,
  fileId: string,
): Promise<string | null> {
  // 1. Get the file path from Telegram
  const fileRes = await fetch(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`);
  if (!fileRes.ok) {
    log.error({ status: fileRes.status }, "Failed to get file from Telegram");
    return null;
  }

  const fileData = (await fileRes.json()) as {
    ok: boolean;
    result?: { file_path?: string };
  };
  const filePath = fileData.result?.file_path;
  if (!filePath) {
    log.error({ fileData }, "Telegram getFile returned no file_path");
    return null;
  }

  // 2. Download the audio from Telegram
  const audioRes = await fetch(`https://api.telegram.org/file/bot${botToken}/${filePath}`);
  if (!audioRes.ok) {
    log.error({ status: audioRes.status }, "Failed to download audio file");
    return null;
  }

  const audioBuffer = Buffer.from(await audioRes.arrayBuffer());
  log.debug({ bytes: audioBuffer.length, filePath }, "Downloaded voice file");

  // 3. Upload to Soniox and transcribe
  const client = new SonioxNodeClient({ api_key: sonioxApiKey });

  const transcription = await client.stt.transcribe({
    model: "stt-async-preview",
    file: audioBuffer,
    filename: filePath.split("/").pop() ?? "voice.ogg",
    language_hints: ["es", "en"],
    wait: true,
    cleanup: ["file", "transcription"],
  });

  const transcript = transcription.transcript;
  const text = transcript?.text?.trim() ?? null;

  if (!text) {
    log.warn("Soniox returned empty transcript");
    return null;
  }

  log.debug({ chars: text.length }, "Transcription complete");
  return text;
}
