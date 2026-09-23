from __future__ import annotations
import json, os, shutil, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request, http.client
from pathlib import Path
from typing import Any
import requests
from progress import progress
TIKHUB_PATH = "/api/v1/douyin/app/v3/fetch_video_high_quality_play_url"
USER_AGENT = "douyin-insight/1.0"
class PipelineError(RuntimeError): pass
def find_key(value: Any, target: str) -> Any:
    if isinstance(value, dict):
        if target in value:
            return value[target]
        for child in value.values():
            found = find_key(child, target)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_key(child, target)
            if found is not None:
                return found
    return None

def request_json(url: str, headers: dict[str, str], payload: dict | None = None, timeout: int = 60, attempts: int = 2) -> tuple[dict, dict[str, str]]:
    data = json.dumps(payload).encode() if payload is not None else None
    all_headers = {"User-Agent": USER_AGENT, "Accept": "application/json", **headers}
    if data is not None:
        all_headers["Content-Type"] = "application/json"
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=data, headers=all_headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body, {key.lower(): value for key, value in response.headers.items()}
        except (urllib.error.URLError, http.client.HTTPException, OSError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    raise PipelineError(str(last_error)) from last_error

def media_url(aweme_id: str) -> tuple[str, str]:
    token = os.getenv("TIKHUB_API_KEY", "").strip()
    if not token:
        raise PipelineError("TIKHUB_API_KEY is not configured")
    base = os.getenv("TIKHUB_BASE_URL", "https://api.tikhub.io").rstrip("/")
    url = f"{base}{TIKHUB_PATH}?{urllib.parse.urlencode({'aweme_id': aweme_id, 'region': 'CN'})}"
    response, _ = request_json(url, {"Authorization": f"Bearer {token}"})
    resolved = find_key(response.get("data"), "original_video_url")
    if not isinstance(resolved, str) or not resolved.startswith(("http://", "https://")):
        raise PipelineError("TikHub response has no original_video_url")
    return resolved, str(response.get("request_id") or "")

def download(url: str, path: Path) -> None:
    last_error: Exception | None = None
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"}
    for attempt in range(3):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(20, 60)) as response:
                response.raise_for_status()
                with path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            if path.stat().st_size:
                return
        except (requests.RequestException, OSError) as error:
            last_error = error
            path.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(2 ** attempt)
    curl = shutil.which("curl")
    if curl:
        partial = path.with_suffix(path.suffix + ".part")
        partial.unlink(missing_ok=True)
        result = subprocess.run([
            curl, "--location", "--fail", "--silent", "--show-error",
            "--retry", "1", "--retry-all-errors", "--retry-delay", "2",
            "--connect-timeout", "15", "--max-time", "120",
            "--continue-at", "-", "--user-agent", headers["User-Agent"],
            "--referer", headers["Referer"], "--output", str(partial), url,
        ], capture_output=True, text=True, timeout=260)
        if result.returncode == 0 and partial.exists() and partial.stat().st_size:
            partial.replace(path)
            return
        partial.unlink(missing_ok=True)
        last_error = PipelineError(f"curl exited {result.returncode}: {result.stderr.strip()[:300]}")
    raise PipelineError(f"media download failed: {last_error}") from last_error

def audio_from_video(video: Path, audio: Path) -> None:
    ffmpeg = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise PipelineError("ffmpeg is not available")
    result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio)], capture_output=True, text=True, timeout=300)
    if result.returncode or not audio.exists() or not audio.stat().st_size:
        raise PipelineError("ffmpeg audio extraction failed: " + result.stderr[:500])

def audio_from_url(url: str, audio: Path) -> None:
    """Stream the account-list play URL directly into audio to avoid huge HQ video downloads."""
    ffmpeg = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise PipelineError("ffmpeg is not available")
    try:
        result = subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-rw_timeout", "15000000", "-user_agent", "Mozilla/5.0", "-i", url,
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio),
        ], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as error:
        raise PipelineError("remote audio extraction timed out") from error
    if result.returncode or not audio.exists() or not audio.stat().st_size:
        raise PipelineError("remote audio extraction failed: " + result.stderr[:500])

def prepare_audio(work: dict, aweme_id: str, video: Path, audio: Path) -> str:
    """Prefer the collected source, retaining a bounded resolver fallback."""
    if work.get("videoUrl"):
        try:
            audio_from_url(work["videoUrl"], audio)
            validate_audio_duration(audio, work.get("durationSeconds"))
            return ""
        except PipelineError:
            try:
                download(work["videoUrl"], video)
                audio_from_video(video, audio)
                validate_audio_duration(audio, work.get("durationSeconds"))
                return ""
            except PipelineError:
                pass
    progress(f"  现有播放地址不可用或音频不完整，正在尝试备用解析……（{aweme_id}）")
    url, request_id = media_url(aweme_id)
    download(url, video)
    audio_from_video(video, audio)
    validate_audio_duration(audio, work.get("durationSeconds"))
    return request_id

def validate_audio_duration(audio: Path, expected: float | None) -> None:
    if not expected:
        return
    result = subprocess.run([os.getenv('FFPROBE_PATH') or 'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio)], capture_output=True, text=True, timeout=20)
    try:
        duration = float(result.stdout.strip())
    except ValueError as error:
        raise PipelineError('Cannot verify audio duration') from error
    if result.returncode or duration < float(expected) - max(3, float(expected) * .01):
        raise PipelineError('Incomplete media duration')

