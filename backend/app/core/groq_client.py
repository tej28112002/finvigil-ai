import requests

from app.core.config import settings

_GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_WHISPER_MODEL = "whisper-large-v3"


def is_configured() -> bool:
    return bool(settings.GROQ_API_KEY)


def transcribe(audio_bytes: bytes, filename: str) -> str:
    """
    Calls Groq's Whisper-compatible transcription API with the audio bytes
    held only in memory — the caller must never write audio_bytes to disk
    or a DB column; JournalService lets this reference drop the moment
    this call returns, which is the actual mechanism satisfying "delete
    raw audio within <5s of successful transcription" (BRD §6).
    Raises RuntimeError (not a network call) if GROQ_API_KEY isn't set,
    so this fails clearly instead of attempting a request that can only
    401.
    """
    if not is_configured():
        raise RuntimeError(
            "Groq STT is not configured. Set GROQ_API_KEY in backend/.env "
            "(from console.groq.com) before recording journal entries."
        )
    response = requests.post(
        _GROQ_TRANSCRIPTION_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        files={"file": (filename, audio_bytes)},
        data={"model": _WHISPER_MODEL},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    text = result.get("text", "").strip()
    if not text:
        raise ValueError("Transcription returned no text — the recording may be silent or too short.")
    return text
