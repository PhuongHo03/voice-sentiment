import subprocess
import logging

logger = logging.getLogger(__name__)


def normalize_to_wav(audio_bytes: bytes) -> bytes:
    """
    Normalizes any input audio (mp3, webm, wav, etc.) to 16kHz, mono, 16-bit PCM WAV
    using ffmpeg through a subprocess.
    """
    if not audio_bytes:
        raise ValueError("Audio content is empty.")

    cmd = [
        "ffmpeg",
        "-y",                    # overwrite output files
        "-i", "pipe:0",          # read input from stdin
        "-f", "wav",             # output format wav
        "-acodec", "pcm_s16le",  # 16-bit signed PCM
        "-ac", "1",              # mono channel
        "-ar", "16000",          # 16000 Hz sample rate
        "pipe:1"                 # write output to stdout
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=audio_bytes)
        
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg failed with code {process.returncode}: {error_msg}")
            raise RuntimeError(f"FFmpeg audio normalization failed: {error_msg}")
        
        logger.info(f"Successfully normalized audio. Original size: {len(audio_bytes)} bytes, Output size: {len(stdout)} bytes")
        return stdout
    except FileNotFoundError as exc:
        logger.error("FFmpeg executable not found. Ensure FFmpeg is installed in the system/container path.")
        raise RuntimeError("FFmpeg executable is not found in PATH.") from exc
    except Exception as exc:
        logger.error(f"Error during audio normalization: {str(exc)}")
        raise
