import json
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LlmTextAnalyticsClient:
    def analyze(self, transcript: list[dict]) -> dict:
        """
        Analyzes the transcript turns using a remote LLM service.
        """
        transcript_text = "\n".join(
            f"[{turn.get('speaker', 'unknown')}] {turn.get('text', '')}" for turn in transcript
        )

        # Real LLM OpenAI-compatible mode
        base_url = settings.llm_base_url.strip()
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            base_url = f"http://{base_url}"

        logger.info(f"Connecting to LLM endpoint: {base_url} (Model: {settings.llm_model})")
        prompt = (
            "Bạn là hệ thống phân tích cuộc gọi tiếng Việt chuyên nghiệp.\n"
            "Hãy đọc đoạn hội thoại sau và trả về DUY NHẤT một chuỗi JSON hợp lệ với định dạng chính xác như sau (không kèm markdown, không kèm giải thích ngoài lề):\n"
            "{\n"
            '  "summary": ["tóm tắt ý 1", "tóm tắt ý 2"],\n'
            '  "sentiment": "positive" | "neutral" | "negative",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.95\n'
            "}\n\n"
            f"Transcript:\n{transcript_text}"
        )

        payload = {
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"

        try:
            with httpx.Client(timeout=60) as client:
                url = f"{base_url.rstrip('/')}/chat/completions"
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"].strip()
            logger.info("Successfully received response from LLM model.")
            
            # Clean up potential markdown formatting in LLM output (e.g. ```json ... ```)
            if content.startswith("```"):
                # Strip leading/trailing codeblock wrappers
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            data = json.loads(content)
            
            # Validate required fields
            return {
                "summary": data.get("summary", ["Không có tóm tắt cuộc gọi."]),
                "sentiment": data.get("sentiment", "neutral"),
                "sentiment_reason": data.get("sentiment_reason", "Không có lý do sắc thái cụ thể."),
                "confidence": float(data.get("confidence", 0.8))
            }
        except httpx.HTTPError as http_exc:
            logger.error(f"LLM API HTTP request failed: {str(http_exc)}")
            raise RuntimeError(f"LLM API call failed: {str(http_exc)}") from http_exc
        except json.JSONDecodeError as json_exc:
            logger.error(f"Failed to parse LLM response content as JSON. Raw output: {content}")
            raise RuntimeError(f"Invalid JSON returned from LLM analytics: {str(json_exc)}") from json_exc
        except Exception as exc:
            logger.error(f"Unexpected error during LLM text analytics: {str(exc)}")
            raise
