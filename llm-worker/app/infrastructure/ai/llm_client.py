import json
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LlmTextAnalyticsClient:
    def analyze(self, transcript: list[dict]) -> dict:
        """
        Analyzes the transcript turns using a remote LLM service.

        For audio transcripts (where speaker labels are "Speaker 0" / "Speaker 1"):
        - Step 1: LLM maps the anonymous speaker IDs to role names ("Nhân viên"/"Khách hàng")
                  based on conversational context. This is now a simple, accurate task because
                  the ONNX diarization has already correctly grouped turns by speaker.
        - Step 2: LLM performs sentiment + summary analysis on the final labeled transcript.

        For text input (where there are no speaker labels), LLM performs role assignment
        and analysis in one pass using the traditional full semantic diarization prompt.
        """
        # Detect whether this is an audio transcript (has ONNX diarization labels)
        has_onnx_labels = any(
            turn.get("speaker", "").startswith("Speaker ")
            for turn in transcript
        )

        if has_onnx_labels:
            return self._analyze_with_onnx_labels(transcript)
        else:
            return self._analyze_text_only(transcript)

    def _analyze_with_onnx_labels(self, transcript: list[dict]) -> dict:
        """
        Two-pass analysis for audio transcripts with ONNX diarization labels.

        Pass 1: Map "Speaker 0"/"Speaker 1" → "Nhân viên"/"Khách hàng"
        Pass 2: Full sentiment + summary analysis on the resolved transcript.
        """
        base_url = self._get_base_url()
        logger.info("Audio transcript detected with ONNX speaker labels. Running role mapping pass...")

        # ── Pass 1: Role mapping ──────────────────────────────────────────────
        speaker_ids = sorted(set(t.get("speaker", "Speaker 0") for t in transcript))

        # Build a short representative excerpt (first 10 turns, max 600 chars)
        excerpt_lines = []
        for turn in transcript[:10]:
            spk = turn.get("speaker", "?")
            text = turn.get("text", "")
            excerpt_lines.append(f"{spk}: {text}")
        excerpt = "\n".join(excerpt_lines)

        role_map_prompt = (
            "Bạn là trợ lý phân tích cuộc hội thoại. Dưới đây là đoạn đầu của một cuộc gọi "
            "giữa hai người nói đã được hệ thống AI nhận diện giọng nói phân chia thành "
            f"{', '.join(speaker_ids)}.\n\n"
            f"Đoạn hội thoại:\n{excerpt}\n\n"
            "Dựa vào nội dung và ngữ cảnh, hãy xác định vai trò của từng người:\n"
            "- 'Nhân viên' là người đại diện cửa hàng/doanh nghiệp để hỗ trợ (thường chào hỏi đầu tiên, hỏi thông tin khách, xác nhận đơn hàng).\n"
            "- 'Khách hàng' là người gọi để mua hàng hoặc được hỗ trợ (thường đặt câu hỏi, đưa ra yêu cầu, cung cấp thông tin cá nhân).\n\n"
            "Trả về JSON đơn giản (không có markdown, không có giải thích):\n"
            '{"speaker_0_role": "Nhân viên hoặc Khách hàng", "speaker_1_role": "Nhân viên hoặc Khách hàng"}'
        )

        role_mapping = {"speaker_0_role": "Khách hàng", "speaker_1_role": "Nhân viên"}  # safe default
        try:
            role_response = self._call_llm(base_url, role_map_prompt)
            parsed = json.loads(role_response)
            r0 = parsed.get("speaker_0_role", "")
            r1 = parsed.get("speaker_1_role", "")
            # Validate — must be one of the two allowed roles
            if r0 in ("Nhân viên", "Khách hàng"):
                role_mapping["speaker_0_role"] = r0
            if r1 in ("Nhân viên", "Khách hàng"):
                role_mapping["speaker_1_role"] = r1
            logger.info(f"Role mapping result: Speaker 0 → '{role_mapping['speaker_0_role']}', Speaker 1 → '{role_mapping['speaker_1_role']}'")
        except Exception as e:
            logger.warning(f"Role mapping LLM call failed, using defaults: {e}")

        # Apply the mapping to produce a fully-labeled transcript
        def _resolve_role(speaker_label: str) -> str:
            if speaker_label == "Speaker 0":
                return role_mapping["speaker_0_role"]
            elif speaker_label == "Speaker 1":
                return role_mapping["speaker_1_role"]
            # Already resolved (text-only path) or unknown
            return speaker_label

        resolved_transcript = [
            {
                "speaker": _resolve_role(turn.get("speaker", "Speaker 0")),
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            }
            for turn in transcript
        ]

        # ── Pass 2: Sentiment, Summary, & Agent Performance analysis ─────────
        logger.info("Running sentiment + summary + agent performance analysis on resolved transcript...")
        analysis_text = "\n".join(
            f"{t['speaker']}: {t['text']}" for t in resolved_transcript
        )
        analysis_prompt = (
            "Bạn là chuyên gia phân tích cuộc gọi chăm sóc khách hàng.\n"
            "Nhiệm vụ của bạn là đọc đoạn hội thoại dưới đây và thực hiện:\n"
            "1. Phân tích sắc thái và tóm tắt cuộc gọi.\n"
            "2. Đánh giá khách quan chất lượng hỗ trợ của Nhân viên (thang điểm 100) và đưa ra 2-4 lời khuyên hành động cụ thể để lần sau họ phục vụ khách hàng tốt hơn.\n\n"
            "Đọc đoạn hội thoại dưới đây và trả về DUY NHẤT một chuỗi JSON hợp lệ "
            "(không kèm markdown, không kèm giải thích ngoài lề) với cấu trúc chính xác:\n"
            "{\n"
            '  "summary": ["tóm tắt ý 1", "tóm tắt ý 2"],\n'
            '  "sentiment": "positive" | "neutral" | "negative",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.95,\n'
            '  "agent_score": 85,\n'
            '  "agent_advice": ["lời khuyên 1", "lời khuyên 2"]\n'
            "}\n\n"
            f"Hội thoại:\n{analysis_text}"
        )
 
        try:
            analysis_response = self._call_llm(base_url, analysis_prompt)
            data = json.loads(analysis_response)
        except Exception as e:
            logger.error(f"Sentiment analysis LLM call failed: {e}")
            data = {}
 
        return {
            "summary": data.get("summary", ["Không có tóm tắt cuộc gọi."]),
            "sentiment": data.get("sentiment", "neutral"),
            "sentiment_reason": data.get("sentiment_reason", "Không có lý do sắc thái cụ thể."),
            "confidence": float(data.get("confidence", 0.8)),
            "agent_score": int(data.get("agent_score", 80)) if data.get("agent_score") is not None else 80,
            "agent_advice": data.get("agent_advice", ["Nên duy trì phong cách hỗ trợ khách hàng lịch sự."]),
            "transcript": resolved_transcript,
        }

    def _analyze_text_only(self, transcript: list[dict]) -> dict:
        """
        Single-pass analysis for text-only input (no ONNX speaker labels).
        LLM performs semantic diarization + sentiment + summary together.
        """
        base_url = self._get_base_url()
        logger.info("Text-only transcript detected. Running combined diarization + analysis pass...")

        transcript_text = "\n".join(
            f"Index {i}: {turn.get('text', '')}" for i, turn in enumerate(transcript)
        )

        prompt = (
            "Bạn là một chuyên gia phân tích cuộc gọi chăm sóc khách hàng bằng tiếng Việt và tiếng Anh chuyên nghiệp.\n"
            "Nhiệm vụ của bạn là đọc đoạn hội thoại thô được chia thành các dòng đánh số (Index) dưới đây, và xác định chính xác vai trò người nói cho từng Index. Vai trò chỉ được phép là 'Khách hàng' hoặc 'Nhân viên'.\n\n"
            "Hướng dẫn phân loại vai trò (Bilingual Rules):\n"
            "- 'Nhân viên' (Employee/Agent): Là người đại diện cho cửa hàng/doanh nghiệp để hỗ trợ. Dấu hiệu nhận biết:\n"
            "  * Chào hỏi khách hàng lúc đầu (ví dụ: 'Thank you for calling...', 'Dạ em chào anh/chị, em giúp gì được...').\n"
            "  * Hỏi thông tin cá nhân của khách để phục vụ (ví dụ: hỏi tên 'May I have your name...', hỏi số điện thoại, hỏi email, địa chỉ giao hàng).\n"
            "  * Lặp lại thông tin khách cung cấp để xác nhận.\n"
            "- 'Khách hàng' (Customer): Là người gọi điện đến để mua hàng, sử dụng dịch vụ hoặc khiếu nại. Dấu hiệu nhận biết:\n"
            "  * Đưa ra yêu cầu đặt hàng, hỏi giá.\n"
            "  * Trả lời và cung cấp thông tin cá nhân khi được hỏi.\n\n"
            "QUY TẮC CỰC KỲ QUAN TRỌNG:\n"
            "1. KHÔNG ĐƯỢC tự động luân phiên (alternate) vai người nói một cách máy móc.\n"
            "2. Một người nói có thể nói liên tục trong nhiều Index tiếp diễn.\n"
            "3. Phân tích thật kỹ ngữ nghĩa toàn bộ cuộc gọi để phân loại chính xác từng dòng.\n"
            "4. Đánh giá khách quan chất lượng hỗ trợ của Nhân viên (thang điểm 100) và đưa ra 2-4 lời khuyên hành động cụ thể để lần sau họ phục vụ khách hàng tốt hơn.\n\n"
            "Hãy trả về DUY NHẤT một chuỗi JSON hợp lệ với định dạng chính xác như sau (không kèm markdown, không kèm giải thích ngoài lề):\n"
            "{\n"
            '  "summary": ["tóm tắt ý 1", "tóm tắt ý 2"],\n'
            '  "sentiment": "positive" | "neutral" | "negative",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.95,\n'
            '  "agent_score": 85,\n'
            '  "agent_advice": ["lời khuyên 1", "lời khuyên 2"],\n'
            '  "speaker_labels": ["vai trò của Index 0", "vai trò của Index 1", ...]\n'
            "}\n\n"
            f"Transcript:\n{transcript_text}"
        )
 
        base_url = self._get_base_url()
        content = self._call_llm(base_url, prompt)
        data = json.loads(content)
 
        labels = data.get("speaker_labels", [])
        corrected_transcript = []
        for i, turn in enumerate(transcript):
            speaker = turn.get("speaker", "Khách hàng")
            if i < len(labels) and labels[i] in ["Khách hàng", "Nhân viên"]:
                speaker = labels[i]
            corrected_transcript.append({
                "speaker": speaker,
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            })
 
        return {
            "summary": data.get("summary", ["Không có tóm tắt cuộc gọi."]),
            "sentiment": data.get("sentiment", "neutral"),
            "sentiment_reason": data.get("sentiment_reason", "Không có lý do sắc thái cụ thể."),
            "confidence": float(data.get("confidence", 0.8)),
            "agent_score": int(data.get("agent_score", 80)) if data.get("agent_score") is not None else 80,
            "agent_advice": data.get("agent_advice", ["Nên duy trì phong cách hỗ trợ khách hàng lịch sự."]),
            "transcript": corrected_transcript,
        }

    # ─────────────────────────────────────────────
    # Shared helpers
    # ─────────────────────────────────────────────
    def _get_base_url(self) -> str:
        base_url = settings.llm_base_url.strip()
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            base_url = f"http://{base_url}"
        logger.info(f"Connecting to LLM endpoint: {base_url} (Model: {settings.llm_model})")
        return base_url

    def _call_llm(self, base_url: str, prompt: str) -> str:
        """
        Calls the remote LLM API (OpenAI-compatible /chat/completions) and returns
        the raw text content of the assistant's reply, with markdown fences stripped.
        Raises RuntimeError on HTTP or JSON errors.
        """
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
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

            # Strip potential markdown fences (```json ... ```)
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            return content

        except httpx.HTTPError as http_exc:
            logger.error(f"LLM API HTTP request failed: {str(http_exc)}")
            raise RuntimeError(f"LLM API call failed: {str(http_exc)}") from http_exc
        except json.JSONDecodeError as json_exc:
            logger.error(f"Failed to parse LLM response as JSON.")
            raise RuntimeError(f"Invalid JSON returned from LLM: {str(json_exc)}") from json_exc
        except Exception as exc:
            logger.error(f"Unexpected error during LLM call: {str(exc)}")
            raise
