from __future__ import annotations
import os, uuid, base64
from pathlib import Path
from media import PipelineError, request_json, find_key
VOLC_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
RESOURCE_ID = "volc.bigasr.auc_turbo"
def volc_headers() -> tuple[dict[str, str], str]:
    request_id = str(uuid.uuid4())
    headers = {"X-Api-Resource-Id": RESOURCE_ID, "X-Api-Request-Id": request_id, "X-Api-Sequence": "-1"}
    api_key = os.getenv("VOLCENGINE_SPEECH_API_KEY", "").strip()
    if api_key:
        headers["X-Api-Key"] = api_key
    else:
        app_id = os.getenv("VOLCENGINE_SPEECH_APP_ID", "").strip()
        token = os.getenv("VOLCENGINE_SPEECH_ACCESS_TOKEN", "").strip()
        if not app_id or not token:
            raise PipelineError("Volcengine speech credentials are not configured")
        headers.update({"X-Api-App-Key": app_id, "X-Api-Access-Key": token})
    return headers, request_id

def transcribe(audio: Path) -> tuple[dict, dict[str, str], str]:
    headers, request_id = volc_headers()
    payload = {"user": {"uid": "benchmark-insight"}, "audio": {"data": base64.b64encode(audio.read_bytes()).decode("ascii")}, "request": {"model_name": "bigmodel", "enable_itn": True, "enable_punc": True, "enable_ddc": True}}
    response, response_headers = request_json(VOLC_ENDPOINT, headers, payload, timeout=300, attempts=1)
    if response_headers.get("x-api-status-code") != "20000000":
        raise PipelineError(f"Volcengine ASR failed: {response_headers.get('x-api-status-code')} {response_headers.get('x-api-message', '')}")
    text = find_key(response, "text")
    if not isinstance(text, str) or not text.strip():
        raise PipelineError("Volcengine ASR returned no speech")
    return response, response_headers, request_id
