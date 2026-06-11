import json
import logging
import re
from datetime import datetime, timezone
import httpx
from app.configs.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Linguistic heuristic weighted keyword patterns for role identification
# Used as a fast, model-agnostic fallback when LLM mapping fails or is invalid
# ─────────────────────────────────────────────
_AGENT_WEIGHTED_PATTERNS = [
    # Strong Agent Indicators (Weight 3.0)
    (r"tổng đài", 3.0),
    (r"chăm sóc khách hàng", 3.0),
    (r"cảm ơn quý khách", 3.0),
    (r"phục vụ", 3.0),
    (r"đường truyền", 3.0),
    (r"giao hàng", 3.0),
    (r"thank you for calling", 3.0),
    (r"how can i (help|assist)", 3.0),
    (r"may i have your", 3.0),
    (r"on behalf of", 3.0),
    (r"what can i get (started|for) you", 3.0),
    (r"for here (or|to) go", 3.0),
    (r"that'll be", 3.0),
    (r"here you go", 3.0),
    (r"you're welcome", 3.0),
    (r"have a good one", 3.0),
    # Medium Agent Indicators (Weight 2.0)
    (r"em chào", 2.0),
    (r"chào anh", 2.0),
    (r"chào chị", 2.0),
    (r"bên em", 2.0),
    (r"bên mình", 2.0),
    (r"xác nhận", 2.0),
    (r"hỗ trợ", 2.0),
    (r"em xin lỗi", 2.0),
    (r"em cảm ơn", 2.0),
    (r"em kiểm tra", 2.0),
    (r"em ghi nhận", 2.0),
    (r"em sẽ", 2.0),
    (r"cho em hỏi", 2.0),
    (r"em có thể", 2.0),
    (r"let me (verify|confirm|check)", 2.0),
    (r"i will (check|look into|process)", 2.0),
    (r"our (team|service|support)", 2.0),
    (r"would you like", 2.0),
    (r"anything else", 2.0),
    (r"is there anything", 2.0),
    (r"welcome to", 2.0),
    # Weak Agent Indicators (Weight 0.5) - Polite words commonly used by both
    (r"\bdạ\b", 0.5),
    (r"\bạ\b", 0.5),
    (r"\bem\b", 0.5),
    (r"dạ em", 0.5),
    (r"dạ anh", 0.5),
    (r"dạ chị", 0.5),
    (r"anh/chị", 0.5),
]

_CUSTOMER_WEIGHTED_PATTERNS = [
    # Strong Customer Indicators (Weight 3.0)
    (r"khiếu nại", 3.0),
    (r"giá bao nhiêu", 3.0),
    (r"báo giá", 3.0),
    (r"hoàn tiền", 3.0),
    (r"đổi trả", 3.0),
    (r"bị lỗi", 3.0),
    (r"không được", 3.0),
    (r"hoàn trả", 3.0),
    (r"hỏng", 3.0),
    (r"how much", 3.0),
    (r"what is the price", 3.0),
    (r"i have a (problem|complaint|question)", 3.0),
    (r"i'll (do|have|go with|take)", 3.0),
    (r"do you have", 3.0),
    (r"can i (get|have|order)", 3.0),
    # Medium Customer Indicators (Weight 2.0)
    (r"tôi muốn", 2.0),
    (r"cho hỏi", 2.0),
    (r"mua hàng", 2.0),
    (r"đặt hàng", 2.0),
    (r"tại sao", 2.0),
    (r"sản phẩm", 2.0),
    (r"tên tôi", 2.0),
    (r"số điện thoại", 2.0),
    (r"địa chỉ", 2.0),
    (r"tôi cần", 2.0),
    (r"i (want|need|would like)", 2.0),
    (r"i('m| am) calling (about|to)", 2.0),
    (r"my (name|number|address|order)", 2.0),
    (r"not today", 2.0),
    (r"thank you so much", 2.0),
    (r"you too", 2.0),
    # Weak Customer Indicators (Weight 1.0)
    (r"anh cần", 1.0),
    (r"chị cần", 1.0),
    (r"cho anh", 1.0),
    (r"cho chị", 1.0),
    (r"\btôi\b", 1.0),
    (r"\banh\b", 1.0),
    (r"\bchị\b", 1.0),
]

_AGENT_RE = [(re.compile(p, re.IGNORECASE), w) for p, w in _AGENT_WEIGHTED_PATTERNS]
_CUSTOMER_RE = [(re.compile(p, re.IGNORECASE), w) for p, w in _CUSTOMER_WEIGHTED_PATTERNS]

_SCORE_CRITERIA = {
    "greeting": {"label": "Chào hỏi và xác lập ngữ cảnh", "max": 10},
    "problem_understanding": {"label": "Hiểu đúng nhu cầu/vấn đề", "max": 20},
    "empathy": {"label": "Đồng cảm và kiểm soát cảm xúc", "max": 20},
    "solution_quality": {"label": "Chất lượng giải pháp/hướng dẫn", "max": 25},
    "process_compliance": {"label": "Tuân thủ quy trình và xác nhận thông tin", "max": 15},
    "closing": {"label": "Chốt cuộc gọi và bước tiếp theo", "max": 10},
}


class LlmTextAnalyticsClient:
    def __init__(self) -> None:
        self._last_provider: dict | None = None

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
        if self._is_low_information_transcript(transcript):
            logger.info("Transcript is too short or low-information. Returning deterministic insufficient-data result.")
            return self._insufficient_information_result(transcript)

        # Detect whether this is an audio transcript (has ONNX diarization labels)
        has_onnx_labels = any(
            turn.get("speaker", "").startswith("Speaker ")
            for turn in transcript
        )

        if has_onnx_labels:
            return self._analyze_with_onnx_labels(transcript)
        else:
            return self._analyze_text_only(transcript)

    def _heuristic_role_mapping(self, transcript: list[dict]) -> dict[str, str]:
        """
        Fast, model-agnostic role mapping based on linguistic keyword scoring.

        For each speaker, computes a weighted score of agent-pattern matches vs customer-pattern
        matches across all their turns. The speaker with the higher agent
        score is assigned 'Nhân viên'; the other gets 'Khách hàng'.

        Returns a dict mapping speaker_id → role (e.g. {"Speaker 0": "Nhân viên", ...}).
        """
        speaker_ids = sorted(set(t.get("speaker", "Speaker 0") for t in transcript))
        scores: dict[str, dict[str, float]] = {spk: {"agent": 0.0, "customer": 0.0} for spk in speaker_ids}

        for turn in transcript:
            spk = turn.get("speaker", "Speaker 0")
            text = turn.get("text", "")
            if spk not in scores:
                scores[spk] = {"agent": 0.0, "customer": 0.0}
            
            # Score agent patterns
            for regex, weight in _AGENT_RE:
                if regex.search(text):
                    scores[spk]["agent"] += weight
                    
            # Score customer patterns
            for regex, weight in _CUSTOMER_RE:
                if regex.search(text):
                    scores[spk]["customer"] += weight

        logger.info(f"Heuristic keyword scores: {scores}")

        # Determine the first turn index for each speaker to use as a robust secondary tie-breaker
        # (Since the Agent/Employee almost always speaks first to greet the customer)
        first_turn_index = {}
        for idx, turn in enumerate(transcript):
            spk = turn.get("speaker", "Speaker 0")
            if spk not in first_turn_index:
                first_turn_index[spk] = idx

        # Rank speakers by agent score (descending); top scorer → Nhân viên
        # Incorporate first-turn tie-breaker: if scores are equal, the speaker who spoke earlier gets a tiny boost
        def _get_ranking_score(spk_id: str) -> float:
            base_score = scores[spk_id]["agent"] - scores[spk_id]["customer"]
            first_turn_idx = first_turn_index.get(spk_id, 999)
            return base_score - (0.001 * first_turn_idx)

        ranked = sorted(speaker_ids, key=_get_ranking_score, reverse=True)

        mapping: dict[str, str] = {}
        roles = ["Nhân viên", "Khách hàng"]
        for idx, spk in enumerate(ranked):
            mapping[spk] = roles[idx] if idx < len(roles) else "Khách hàng"

        logger.info(f"Heuristic role mapping result: {mapping}")
        return mapping

    def _analyze_with_onnx_labels(self, transcript: list[dict]) -> dict:
        """
        Two-pass analysis for audio transcripts with ONNX diarization labels.

        Pass 1: Map "Speaker 0"/"Speaker 1" → "Nhân viên"/"Khách hàng"
                via LLM semantic understanding. If the LLM fails or returns
                invalid/identical roles, falls back to keyword heuristics.
        Pass 2: Full sentiment + summary analysis on the resolved transcript.
        """
        base_url = self._get_base_url()
        logger.info("Audio transcript detected with ONNX speaker labels. Running role mapping pass...")

        # ── Pass 1: Role mapping with Multi-point Context Sampler ───────────
        speaker_ids = sorted(set(t.get("speaker", "Speaker 0") for t in transcript))

        # Select chronological indices of turns to include in the excerpt
        selected_indices = set()
        total_turns = len(transcript)
        
        # 1. First 8 turns (captures initial greetings / phone openings)
        for i in range(min(8, total_turns)):
            selected_indices.add(i)
            
        # 2. Last 4 turns (captures goodbye and thank-yous)
        for i in range(max(0, total_turns - 4), total_turns):
            selected_indices.add(i)
            
        # 3. Middle segment: select up to 8 longest turns for each speaker ID
        rest_turns = [(idx, t) for idx, t in enumerate(transcript) if idx not in selected_indices]
        for spk_id in speaker_ids:
            # Filter turns belonging to this speaker
            spk_turns = [item for item in rest_turns if item[1].get("speaker") == spk_id]
            # Sort by text length descending
            spk_turns_sorted = sorted(spk_turns, key=lambda item: len(item[1].get("text", "")), reverse=True)
            # Take top 8 longest turns
            for item in spk_turns_sorted[:8]:
                selected_indices.add(item[0])
                
        # Build the final excerpt in strict chronological order
        excerpt_lines = []
        for idx in sorted(selected_indices):
            turn = transcript[idx]
            spk = turn.get("speaker", "?")
            text = turn.get("text", "")
            excerpt_lines.append(f"[{idx}] {spk}: {text}")
        excerpt = "\n".join(excerpt_lines)

        # Build a dynamic JSON schema string keyed by the actual speaker IDs
        json_schema = "{" + ", ".join(f'"{spk}": "Nhân viên hoặc Khách hàng"' for spk in speaker_ids) + "}"

        role_map_prompt = (
            "Bạn là chuyên gia phân tích cuộc gọi chăm sóc khách hàng tiếng Việt và tiếng Anh.\n"
            "Dưới đây là một số câu thoại chọn lọc đại diện theo đúng trình tự thời gian từ cuộc gọi. "
            f"Hệ thống đã tự động phân cụm thành các người nói: {', '.join(speaker_ids)}.\n\n"
            f"Các câu thoại mẫu (với số thứ tự dòng [idx]):\n{excerpt}\n\n"
            "Hãy phân tích Ý ĐỊNH CỐT LÕI (Core Intent) và cách xưng hô của từng người nói để xác định chính xác vai trò. Chỉ có 2 vai trò:\n"
            "- 'Nhân viên': Đại diện doanh nghiệp/cửa hàng. DẤU HIỆU NHẬN BIẾT:\n"
            "  * Ý định: Chủ động chào hỏi, cung cấp sự trợ giúp, hướng dẫn giải quyết vấn đề, tra cứu thông tin trên hệ thống, xác nhận đơn hàng/lịch hẹn.\n"
            "  * Từ ngữ đặc trưng: Dùng các từ 'dạ/ạ' ở đầu/cuối câu, xưng 'em' và gọi khách là 'anh/chị/quý khách', dùng các cụm như 'bên em', 'tổng đài', 'cửa hàng', 'hỗ trợ cho mình'.\n"
            "  * Tiếng Anh: 'Thank you for calling', 'How can I help/assist you', 'on behalf of', 'let me check'.\n"
            "- 'Khách hàng': Người gọi điện để yêu cầu hỗ trợ hoặc mua sắm. DẤU HIỆU NHẬN BIẾT:\n"
            "  * Ý định: Đặt câu hỏi, yêu cầu phục vụ, phản ánh sự cố/khiếu nại, cung cấp thông tin cá nhân (tên, số điện thoại, địa chỉ) khi được hỏi.\n"
            "  * Từ ngữ đặc trưng: Đưa ra yêu cầu ('cho tôi hỏi', 'tôi muốn', 'bị lỗi rồi', 'không làm được'), xưng hô tự nhiên hoặc có thể xưng 'dạ/ạ' nếu lịch sự (nhưng ý định cốt lõi vẫn là hỏi/khiếu nại).\n"
            "  * Tiếng Anh: 'I want to', 'I need', 'I'm calling because', 'my order is'.\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Hai người nói chính PHẢI có hai vai trò KHÁC NHAU (một Nhân viên, một Khách hàng).\n"
            "2. Đánh giá dựa trên Ý ĐỊNH CỐT LÕI (ai là người hỏi/cần giúp và ai là người trả lời/hỗ trợ) — KHÔNG chỉ dựa vào kính ngữ dạ/ạ (vì khách hàng lịch sự vẫn có thể dùng dạ/ạ).\n"
            "3. Trả về duy nhất JSON đơn giản khớp với schema sau (không giải thích thêm, không dùng markdown):\n"
            f"{json_schema}"
        )

        # Safe default: Speaker 0 is customer, Speaker 1 is agent (most common phone-call pattern)
        default_mapping: dict[str, str] = {}
        for idx, spk in enumerate(speaker_ids):
            default_mapping[spk] = "Nhân viên" if idx == 1 else "Khách hàng"

        role_mapping = dict(default_mapping)
        llm_mapping_ok = False

        try:
            parsed = self._call_llm_json(base_url, role_map_prompt)

            candidate: dict[str, str] = {}
            for spk in speaker_ids:
                role = parsed.get(spk, "")
                if role in ("Nhân viên", "Khách hàng"):
                    candidate[spk] = role

            # Validate: all speaker IDs must be present AND roles must not all be identical
            roles_set = set(candidate.values())
            if len(candidate) == len(speaker_ids) and len(roles_set) > 1:
                role_mapping = candidate
                llm_mapping_ok = True
                logger.info(f"LLM role mapping result: {role_mapping}")
            else:
                logger.warning(
                    f"LLM returned invalid/identical roles ({candidate}). "
                    "Falling back to heuristic mapping."
                )
        except Exception as e:
            logger.warning(f"Role mapping LLM call failed ({e}). Falling back to heuristic mapping.")

        # Heuristic fallback if LLM produced invalid results
        if not llm_mapping_ok:
            heuristic_mapping = self._heuristic_role_mapping(transcript)
            # Only use heuristic if it produced a valid, distinct mapping
            heuristic_roles = set(heuristic_mapping.values())
            if len(heuristic_roles) > 1:
                role_mapping = heuristic_mapping
                logger.info("Heuristic fallback applied successfully.")
            else:
                role_mapping = default_mapping
                logger.warning("Heuristic also produced identical roles. Using default mapping.")

        # Apply the mapping to produce a fully-labeled transcript
        def _resolve_role(speaker_label: str) -> str:
            return role_mapping.get(speaker_label, speaker_label)

        resolved_transcript = [
            {
                "index": idx,
                "speaker": _resolve_role(turn.get("speaker", "Speaker 0")),
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            }
            for idx, turn in enumerate(transcript)
        ]

        resolved_transcript = self._refine_transcript_roles(resolved_transcript, base_url)

        if settings.enable_detailed_summary:
            try:
                return self._run_structured_pipeline(resolved_transcript)
            except Exception as e:
                logger.error(f"Structured analysis pipeline failed. Falling back to legacy analysis: {e}")

        return self._legacy_analyze_resolved_transcript(resolved_transcript)

    def _analyze_text_only(self, transcript: list[dict]) -> dict:
        """
        Single-pass analysis for text-only input (no ONNX speaker labels).
        LLM performs semantic diarization + sentiment + summary together.
        """
        base_url = self._get_base_url()
        logger.info("Text-only transcript detected. Running combined diarization + analysis pass...")

        if settings.enable_detailed_summary:
            try:
                corrected_transcript = self._resolve_text_only_roles(transcript, base_url)
                return self._run_structured_pipeline(corrected_transcript)
            except Exception as e:
                logger.error(f"Structured text-only analysis failed. Falling back to legacy analysis: {e}")

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
            "QUY TẮC ĐÁNH GIÁ ĐIỂM NHÂN VIÊN (agent_score - Thang điểm 100):\n"
            "- agent_score đại diện cho CHẤT LƯỢNG HỖ TRỢ của Nhân viên, chứ không phải tâm trạng của Khách hàng.\n"
            "- Nếu cuộc gọi quá ngắn hoặc KHÔNG CÓ bất kỳ lượt nói nào của Nhân viên (chỉ có Khách hàng nói một mình):\n"
            "  * Gán điểm mặc định là 80 nếu sắc thái cuộc gọi là Tích cực hoặc Trung lập (chưa thể hiện lỗi gì của nhân viên).\n"
            "  * Gán điểm mặc định là 50 nếu sắc thái cuộc gọi là Tiêu cực (nhắc nhở nhân viên cần chủ động phản hồi xoa dịu khách), tuyệt đối KHÔNG được đánh giá 0 hoặc 100 điểm một cách tùy tiện.\n"
            "- Nếu cuộc gọi có đầy đủ tương tác:\n"
            "  * Sắc thái Trung lập (Neutral): Điểm nhân viên nên nằm trong khoảng 70 - 85, trừ khi nhân viên làm việc xuất sắc (90+) hoặc tệ hại (dưới 50). Không cho 0 hay 100 điểm một cách vô lý.\n"
            "  * Sắc thái Tiêu cực (Negative): Nếu khách hàng giận dữ về sản phẩm nhưng Nhân viên vẫn lịch sự, bình tĩnh hỗ trợ đúng quy trình, điểm của nhân viên vẫn phải ở mức Khá (70 - 85). Không đánh giá 0 điểm trừ khi nhân viên thô lỗ, cãi cọ hoặc phớt lờ khách hàng.\n"
            "  * Sắc thái Tích cực (Positive): Điểm nhân viên xứng đáng ở mức 80 - 100.\n\n"
            "Allowed values: sentiment chỉ được là một trong các giá trị positive, neutral, negative. "
            "speaker_labels là mảng có đúng một nhãn cho mỗi Index, mỗi nhãn chỉ được là Khách hàng hoặc Nhân viên.\n"
            "Hãy trả về DUY NHẤT một JSON hợp lệ với định dạng chính xác như ví dụ sau (không kèm markdown, không kèm giải thích ngoài lề):\n"
            "{\n"
            '  "summary": ["tóm tắt ý 1", "tóm tắt ý 2"],\n'
            '  "sentiment": "neutral",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.95,\n'
            '  "agent_score": 85,\n'
            '  "agent_advice": ["lời khuyên 1", "lời khuyên 2"],\n'
            '  "speaker_labels": ["Khách hàng", "Nhân viên"]\n'
            "}\n\n"
            f"Transcript:\n{transcript_text}"
        )
 
        base_url = self._get_base_url()
        data = self._call_llm_json(base_url, prompt)
 
        labels = data.get("speaker_labels", [])
        corrected_transcript = []
        for i, turn in enumerate(transcript):
            speaker = turn.get("speaker", "Khách hàng")
            if i < len(labels) and labels[i] in ["Khách hàng", "Nhân viên"]:
                speaker = labels[i]
            corrected_transcript.append({
                "index": i,
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

    def _resolve_text_only_roles(self, transcript: list[dict], base_url: str) -> list[dict]:
        normalized_transcript = []
        for i, turn in enumerate(transcript):
            normalized_transcript.append({
                "index": i,
                "speaker": turn.get("speaker", "unknown"),
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            })
        return self._refine_transcript_roles(normalized_transcript, base_url)

    def _refine_transcript_roles(self, transcript: list[dict], base_url: str) -> list[dict]:
        normalized_transcript = self._mark_system_turns(transcript)
        chunks = self._chunk_transcript(normalized_transcript, max_turns=35, overlap=4)
        labels_by_index: dict[int, str] = {}

        for chunk in chunks:
            labels_by_index.update(self._refine_role_chunk(base_url, chunk))

        corrected_transcript = []
        for i, turn in enumerate(normalized_transcript):
            idx = self._int(turn.get("index"), i, 0, max(len(normalized_transcript) - 1, 0))
            speaker = labels_by_index.get(idx, turn.get("speaker", "Khách hàng"))
            if speaker not in ["Khách hàng", "Nhân viên", "Hệ thống"]:
                speaker = turn.get("speaker", "Khách hàng")
            corrected_transcript.append({
                "index": idx,
                "speaker": speaker,
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            })
        return corrected_transcript

    def _refine_role_chunk(self, base_url: str, transcript: list[dict]) -> dict[int, str]:
        transcript_text = self._format_transcript(transcript)
        prompt = (
            "Bạn là chuyên gia phân vai theo ngữ nghĩa cho transcript chăm sóc khách hàng tiếng Việt/Anh.\n"
            "Hãy đọc transcript bên dưới và gán vai trò CHO TỪNG Index dựa trên nội dung câu nói và ngữ cảnh lân cận.\n\n"
            "Vai trò hợp lệ:\n"
            "- 'Nhân viên': người đại diện doanh nghiệp, đặt câu hỏi xác minh, hướng dẫn, giải thích, xin lỗi, chốt hỗ trợ.\n"
            "- 'Khách hàng': người nhận hỗ trợ, trả lời thông tin cá nhân, xác nhận yes/no/okay, hỏi lại, nêu nhu cầu hoặc vấn đề.\n"
            "- 'Hệ thống': intro/outro quảng cáo, podcast, lời dẫn recording, nội dung không thuộc cuộc gọi giữa khách và nhân viên.\n\n"
            "Quy tắc bắt buộc:\n"
            "- Tôn trọng speaker hiện có khi nội dung không đủ chắc chắn để đổi vai.\n"
            "- Không gán mọi dòng cho cùng một vai nếu có hỏi-đáp rõ ràng.\n"
            "- Câu trả lời ngắn, số, tên riêng sau câu hỏi xác minh thường là Khách hàng.\n"
            "- Intro/outro/quảng cáo/lời dẫn recording phải là Hệ thống.\n"
            "- Trả đúng nhãn cho từng Index trong chunk.\n\n"
            "Trả về DUY NHẤT JSON hợp lệ:\n"
            '{ "speaker_labels": [{"index": 0, "speaker": "Hệ thống"}, {"index": 1, "speaker": "Nhân viên"}] }\n\n'
            f"Transcript:\n{transcript_text}"
        )
        try:
            data = self._call_llm_json(base_url, prompt)
            labels = data.get("speaker_labels", [])
        except Exception as exc:
            logger.warning(f"Semantic role refinement failed: {exc}. Keeping existing speaker labels.")
            return {}

        labels_by_index: dict[int, str] = {}
        if isinstance(labels, list):
            for fallback_idx, item in enumerate(labels):
                if isinstance(item, dict):
                    idx = self._int(item.get("index"), -1, -1, 10_000_000)
                    speaker = item.get("speaker")
                else:
                    idx = self._int(transcript[fallback_idx].get("index"), fallback_idx, 0, 10_000_000) if fallback_idx < len(transcript) else -1
                    speaker = item
                if idx >= 0 and speaker in ["Khách hàng", "Nhân viên", "Hệ thống"]:
                    labels_by_index[idx] = speaker
        return labels_by_index

    def _mark_system_turns(self, transcript: list[dict]) -> list[dict]:
        marked = []
        previous_system = False
        for i, turn in enumerate(transcript):
            raw_text = str(turn.get("text", "")).strip()
            text = raw_text.lower()
            speaker = turn.get("speaker", "Khách hàng")
            if self._is_system_utterance(text) or (previous_system and self._looks_like_system_continuation(text)):
                speaker = "Hệ thống"
            marked.append({
                "index": turn.get("index", i),
                "speaker": speaker,
                "text": raw_text,
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            })
            previous_system = speaker == "Hệ thống"
        return marked

    def _is_system_utterance(self, text: str) -> bool:
        patterns = [
            "you're listening to",
            "you are listening to",
            "podcast",
            "inbound call recording",
            "find out more",
            "log on to",
            "visit www",
            "toll-free",
            "our services by visiting",
            "numbers from u",
        ]
        return any(pattern in text for pattern in patterns)

    def _looks_like_system_continuation(self, text: str) -> bool:
        continuation_patterns = [
            "www",
            ".com",
            "http",
            "toll",
            "free",
            "services",
            "numbers",
            "visit",
            "website",
            "hotline",
        ]
        return any(pattern in text for pattern in continuation_patterns)

    def _legacy_analyze_resolved_transcript(self, resolved_transcript: list[dict]) -> dict:
        base_url = self._get_base_url()
        logger.info("Running legacy sentiment + summary + agent performance analysis...")
        analysis_text = "\n".join(
            f"{t.get('speaker', '')}: {t.get('text', '')}" for t in resolved_transcript
        )
        analysis_prompt = (
            "Bạn là chuyên gia phân tích cuộc gọi chăm sóc khách hàng.\n"
            "Nhiệm vụ của bạn là đọc đoạn hội thoại dưới đây và thực hiện:\n"
            "1. Phân tích sắc thái và tóm tắt cuộc gọi.\n"
            "2. Đánh giá khách quan chất lượng hỗ trợ của Nhân viên (thang điểm 100) và đưa ra 2-4 lời khuyên hành động cụ thể để lần sau họ phục vụ khách hàng tốt hơn.\n\n"
            "QUY TẮC ĐÁNH GIÁ ĐIỂM NHÂN VIÊN (agent_score - Thang điểm 100):\n"
            "- agent_score đại diện cho CHẤT LƯỢNG HỖ TRỢ của Nhân viên, chứ không phải tâm trạng của Khách hàng.\n"
            "- Nếu cuộc gọi quá ngắn hoặc KHÔNG CÓ bất kỳ lượt nói nào của Nhân viên (chỉ có Khách hàng nói một mình):\n"
            "  * Gán điểm mặc định là 80 nếu sắc thái cuộc gọi là Tích cực hoặc Trung lập.\n"
            "  * Gán điểm mặc định là 50 nếu sắc thái cuộc gọi là Tiêu cực, tuyệt đối không đánh giá 0 hoặc 100 tùy tiện.\n"
            "- Nếu cuộc gọi có đầy đủ tương tác, điểm phải phản ánh cách Nhân viên xử lý, không chỉ phản ánh tâm trạng Khách hàng.\n\n"
            "Trả về DUY NHẤT JSON hợp lệ:\n"
            "Allowed values: sentiment chỉ được là positive, neutral hoặc negative.\n"
            "{\n"
            '  "summary": ["tóm tắt ý 1", "tóm tắt ý 2"],\n'
            '  "sentiment": "neutral",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.95,\n'
            '  "agent_score": 85,\n'
            '  "agent_advice": ["lời khuyên 1", "lời khuyên 2"]\n'
            "}\n\n"
            f"Hội thoại:\n{analysis_text}"
        )

        try:
            data = self._call_llm_json(base_url, analysis_prompt)
        except Exception as e:
            logger.error(f"Legacy sentiment analysis LLM call failed: {e}")
            data = {}

        return {
            "summary": self._string_list(data.get("summary"), ["Không có tóm tắt cuộc gọi."], limit=5),
            "detailed_summary": None,
            "sentiment": self._sentiment(data.get("sentiment")),
            "sentiment_reason": self._text(data.get("sentiment_reason"), "Không có lý do sắc thái cụ thể.", 1000),
            "confidence": self._float(data.get("confidence"), 0.8, 0.0, 1.0),
            "agent_score": self._int(data.get("agent_score"), 80, 0, 100),
            "agent_score_breakdown": None,
            "quality_notes": [],
            "agent_advice": self._string_list(data.get("agent_advice"), ["Nên duy trì phong cách hỗ trợ khách hàng lịch sự."], limit=4),
            "analysis_metadata": self._analysis_metadata("legacy_single_pass"),
            "transcript": resolved_transcript,
        }

    def _run_structured_pipeline(self, resolved_transcript: list[dict]) -> dict:
        base_url = self._get_base_url()
        analysis_transcript = self._call_turns(resolved_transcript)
        if self._is_low_information_transcript(analysis_transcript):
            return self._insufficient_information_result(resolved_transcript)

        transcript_text = self._format_transcript(analysis_transcript)
        logger.info("Running structured multi-pass call analysis pipeline...")

        facts = self._extract_facts_for_transcript(base_url, analysis_transcript)
        summary_transcript = self._format_transcript(self._analysis_excerpt(analysis_transcript))
        summary_result = self._generate_detailed_summary(base_url, summary_transcript, facts, analysis_transcript)
        evaluation = self._evaluate_agent_performance(base_url, summary_transcript, facts, summary_result, analysis_transcript)

        return self._compose_structured_result(resolved_transcript, facts, summary_result, evaluation)

    def _extract_facts_for_transcript(self, base_url: str, transcript: list[dict]) -> dict:
        chunks = self._chunk_transcript(transcript, max_turns=45, overlap=5)
        if len(chunks) <= 1:
            return self._extract_call_facts(base_url, self._format_transcript(transcript), transcript)

        logger.info(f"Long transcript detected. Extracting call facts in {len(chunks)} chunks...")
        chunk_facts = [
            self._extract_call_facts(base_url, self._format_transcript(chunk), chunk)
            for chunk in chunks
        ]
        return self._merge_fact_sets(chunk_facts)

    def _extract_call_facts(self, base_url: str, transcript_text: str, transcript: list[dict]) -> dict:
        prompt = (
            "Bạn là chuyên viên QA cuộc gọi. Nhiệm vụ ở bước này CHỈ là trích xuất sự thật từ transcript, chưa tóm tắt văn phong và chưa chấm điểm.\n"
            "Quy tắc bắt buộc:\n"
            "- Chỉ dùng thông tin xuất hiện trong transcript.\n"
            "- Toàn bộ text phân tích phải viết bằng tiếng Việt, chỉ giữ nguyên tên riêng/thuật ngữ tiếng Anh khi cần.\n"
            "- Không dùng intro/outro, podcast, quảng cáo hoặc lời dẫn recording làm facts của cuộc gọi.\n"
            "- Không bịa tên, giá, chính sách, deadline hoặc cam kết.\n"
            "- Nếu deadline/owner không rõ, dùng null hoặc 'Chưa xác định'.\n"
            "- evidence_turns là danh sách Index có trong transcript, giữ nguyên số Index gốc.\n"
            "- Phân biệt rõ: Nhân viên là người hỏi/xác minh/hướng dẫn; Khách hàng là người trả lời thông tin, đồng ý/từ chối/hỏi lại.\n\n"
            "Allowed values:\n"
            "- customer_pain_points[].severity: low, medium, high.\n"
            "- agent_actions[].action_type: clarify, explain, apologize, resolve, escalate, follow_up, other.\n"
            "- commitments[].owner: Nhân viên, Khách hàng, Chưa xác định.\n"
            "- outcome.status: resolved, unresolved, follow_up_required, unclear.\n"
            "Trả về DUY NHẤT JSON hợp lệ theo schema:\n"
            "{\n"
            '  "customer_needs": [{"text": "...", "evidence_turns": [0]}],\n'
            '  "customer_pain_points": [{"text": "...", "severity": "medium", "evidence_turns": [0]}],\n'
            '  "agent_actions": [{"text": "...", "action_type": "clarify", "evidence_turns": [1]}],\n'
            '  "commitments": [{"owner": "Nhân viên", "commitment": "...", "deadline": null, "evidence_turns": [2]}],\n'
            '  "outcome": {"status": "unclear", "description": "...", "evidence_turns": [3]},\n'
            '  "important_moments": [{"title": "...", "description": "...", "time_range": "mm:ss-mm:ss", "evidence_turns": [0, 1]}]\n'
            "}\n\n"
            f"Transcript:\n{transcript_text}"
        )
        data = self._call_llm_json(base_url, prompt)
        valid_indexes = self._valid_indexes(transcript)
        return {
            "customer_needs": self._sanitize_fact_items(data.get("customer_needs"), valid_indexes, limit=8),
            "customer_pain_points": self._sanitize_fact_items(data.get("customer_pain_points"), valid_indexes, limit=8),
            "agent_actions": self._sanitize_fact_items(data.get("agent_actions"), valid_indexes, limit=10),
            "commitments": self._sanitize_fact_items(data.get("commitments"), valid_indexes, limit=8),
            "outcome": self._sanitize_fact_item(data.get("outcome"), valid_indexes, default={"status": "unclear", "description": "", "evidence_turns": []}),
            "important_moments": self._sanitize_fact_items(data.get("important_moments"), valid_indexes, limit=10),
        }

    def _generate_detailed_summary(self, base_url: str, transcript_text: str, facts: dict, transcript: list[dict]) -> dict:
        facts_text = json.dumps(facts, ensure_ascii=False)
        prompt = (
            "Bạn là chuyên gia viết call notes cho đội chăm sóc khách hàng. "
            "Dựa trên transcript và facts đã trích xuất, hãy tạo bản tóm tắt có cấu trúc, cụ thể và không chung chung.\n"
            "Quy tắc bắt buộc:\n"
            "- Viết toàn bộ phần phân tích bằng tiếng Việt, chỉ giữ nguyên tên riêng/sản phẩm/thuật ngữ tiếng Anh khi cần.\n"
            "- summary gồm 3-5 ý ngắn, đủ hiểu toàn cuộc gọi.\n"
            "- overview dài 2-4 câu.\n"
            "- Không bịa thông tin ngoài transcript/facts.\n"
            "- Không biến object/dict thành chuỗi text; các danh sách phải là câu tiếng Việt tự nhiên.\n"
            "- Không đưa intro/outro podcast/quảng cáo vào summary.\n"
            "- Nếu không có action item hoặc rủi ro, trả mảng rỗng.\n"
            "- evidence_turns phải là Index xuất hiện trong transcript, giữ nguyên số Index gốc.\n\n"
            "Allowed values:\n"
            "- action_items[].owner: Nhân viên, Khách hàng, Chưa xác định.\n"
            "- action_items[].priority: low, medium, high.\n"
            "Trả về DUY NHẤT JSON hợp lệ:\n"
            "{\n"
            '  "summary": ["ý chính 1", "ý chính 2", "ý chính 3"],\n'
            '  "detailed_summary": {\n'
            '    "overview": "...",\n'
            '    "key_takeaways": ["..."],\n'
            '    "topics": [{"title": "...", "time_range": "mm:ss-mm:ss", "details": ["..."], "evidence_turns": [0]}],\n'
            '    "customer_needs": ["..."],\n'
            '    "customer_pain_points": ["..."],\n'
            '    "agent_actions": ["..."],\n'
            '    "outcome": "...",\n'
            '    "next_steps": ["..."],\n'
            '    "action_items": [{"owner": "Nhân viên", "task": "...", "deadline": null, "priority": "medium", "evidence_turns": [0]}],\n'
            '    "risks_or_escalations": ["..."]\n'
            "  }\n"
            "}\n\n"
            f"Facts:\n{facts_text}\n\nTranscript:\n{transcript_text}"
        )
        data = self._call_llm_json(base_url, prompt)
        return self._sanitize_summary_result(data, transcript, facts)

    def _evaluate_agent_performance(self, base_url: str, transcript_text: str, facts: dict, summary_result: dict, transcript: list[dict]) -> dict:
        facts_text = json.dumps(facts, ensure_ascii=False)
        summary_text = json.dumps(summary_result, ensure_ascii=False)
        rubric = json.dumps(_SCORE_CRITERIA, ensure_ascii=False)
        prompt = (
            "Bạn là trưởng nhóm QA chăm sóc khách hàng. Hãy đánh giá sắc thái cuộc gọi và chất lượng hỗ trợ của Nhân viên.\n"
            "Quy tắc bắt buộc:\n"
            "- Viết toàn bộ lý do, quality_notes và agent_advice bằng tiếng Việt.\n"
            "- agent_score đánh giá chất lượng hỗ trợ của Nhân viên, không phải chỉ tâm trạng Khách hàng.\n"
            "- sentiment là sắc thái thực tế của khách trong cuộc gọi. Nếu khách chủ yếu trả lời xác nhận ngắn, không phàn nàn, hãy chọn neutral hoặc positive có lý do cụ thể.\n"
            "- Nếu khách bức xúc vì sản phẩm nhưng Nhân viên vẫn lịch sự, đúng quy trình, không được cho điểm quá thấp.\n"
            "- Nếu không có lượt nói rõ ràng của Nhân viên, dùng điểm mặc định hợp lý: 80 nếu positive/neutral, 50 nếu negative.\n"
            "- Score từng tiêu chí không vượt max trong rubric. quality_notes phải cụ thể, dựa trên transcript.\n"
            "- agent_advice phải là khuyến nghị hành động liên quan trực tiếp tới điểm yếu trong quality_notes; không viết lời cảm ơn/quảng cáo/podcast hoặc câu chung chung.\n\n"
            f"Rubric:\n{rubric}\n\n"
            "Trả về DUY NHẤT JSON hợp lệ:\n"
            "Allowed values: sentiment chỉ được là positive, neutral hoặc negative.\n"
            "{\n"
            '  "sentiment": "neutral",\n'
            '  "sentiment_reason": "lý do cụ thể bằng tiếng Việt",\n'
            '  "confidence": 0.92,\n'
            '  "agent_score": 86,\n'
            '  "agent_score_breakdown": {\n'
            '    "greeting": {"score": 8, "max": 10, "reason": "..."},\n'
            '    "problem_understanding": {"score": 18, "max": 20, "reason": "..."},\n'
            '    "empathy": {"score": 16, "max": 20, "reason": "..."},\n'
            '    "solution_quality": {"score": 22, "max": 25, "reason": "..."},\n'
            '    "process_compliance": {"score": 13, "max": 15, "reason": "..."},\n'
            '    "closing": {"score": 9, "max": 10, "reason": "..."}\n'
            "  },\n"
            '  "quality_notes": ["điểm mạnh/yếu cụ thể"],\n'
            '  "agent_advice": ["lời khuyên hành động cụ thể"]\n'
            "}\n\n"
            f"Facts:\n{facts_text}\n\nSummary:\n{summary_text}\n\nTranscript:\n{transcript_text}"
        )
        data = self._call_llm_json(base_url, prompt)
        return self._sanitize_evaluation(data, transcript)

    def _compose_structured_result(self, transcript: list[dict], facts: dict, summary_result: dict, evaluation: dict) -> dict:
        metadata = self._analysis_metadata("multi_pass")
        metadata["facts"] = facts
        return {
            "summary": summary_result["summary"],
            "detailed_summary": summary_result["detailed_summary"],
            "sentiment": evaluation["sentiment"],
            "sentiment_reason": evaluation["sentiment_reason"],
            "confidence": evaluation["confidence"],
            "agent_score": evaluation["agent_score"],
            "agent_score_breakdown": evaluation["agent_score_breakdown"],
            "quality_notes": evaluation["quality_notes"],
            "agent_advice": evaluation["agent_advice"],
            "analysis_metadata": metadata,
            "transcript": transcript,
        }

    def _is_low_information_transcript(self, transcript: list[dict]) -> bool:
        texts = [
            str(turn.get("text", "")).strip()
            for turn in transcript
            if turn.get("speaker") != "Hệ thống" and str(turn.get("text", "")).strip()
        ]
        if not texts:
            return True

        combined = " ".join(texts)
        word_count = len(re.findall(r"\w+", combined, flags=re.UNICODE))
        return len(combined) < 30 or word_count < 8

    def _call_turns(self, transcript: list[dict]) -> list[dict]:
        return [turn for turn in transcript if turn.get("speaker") != "Hệ thống"]

    def _chunk_transcript(self, transcript: list[dict], max_turns: int, overlap: int = 0) -> list[list[dict]]:
        if len(transcript) <= max_turns:
            return [transcript]
        chunks = []
        start = 0
        step = max(1, max_turns - overlap)
        while start < len(transcript):
            chunk = transcript[start:start + max_turns]
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks

    def _analysis_excerpt(self, transcript: list[dict], max_turns: int = 90) -> list[dict]:
        if len(transcript) <= max_turns:
            return transcript
        head_count = max_turns // 3
        tail_count = max_turns // 3
        middle_count = max_turns - head_count - tail_count
        middle_start = max(0, (len(transcript) - middle_count) // 2)
        excerpt = (
            transcript[:head_count]
            + transcript[middle_start:middle_start + middle_count]
            + transcript[-tail_count:]
        )
        seen = set()
        deduped = []
        for turn in excerpt:
            idx = turn.get("index")
            if idx not in seen:
                deduped.append(turn)
                seen.add(idx)
        return deduped

    def _merge_fact_sets(self, fact_sets: list[dict]) -> dict:
        merged = {
            "customer_needs": [],
            "customer_pain_points": [],
            "agent_actions": [],
            "commitments": [],
            "outcome": {"status": "unclear", "description": "", "evidence_turns": []},
            "important_moments": [],
        }
        for facts in fact_sets:
            for key in ["customer_needs", "customer_pain_points", "agent_actions", "commitments", "important_moments"]:
                merged[key].extend(facts.get(key, []))
            outcome = facts.get("outcome")
            if isinstance(outcome, dict) and outcome.get("description"):
                merged["outcome"] = outcome

        for key, limit in [
            ("customer_needs", 10),
            ("customer_pain_points", 10),
            ("agent_actions", 14),
            ("commitments", 10),
            ("important_moments", 12),
        ]:
            merged[key] = self._dedupe_fact_items(merged[key])[:limit]
        return merged

    def _dedupe_fact_items(self, items: list[dict]) -> list[dict]:
        deduped = []
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            key = self._text(item.get("text") or item.get("description") or item.get("commitment"), "", 160).lower()
            evidence_key = tuple(item.get("evidence_turns") or [])
            marker = (key, evidence_key)
            if marker not in seen:
                deduped.append(item)
                seen.add(marker)
        return deduped

    def _insufficient_information_result(self, transcript: list[dict]) -> dict:
        normalized_transcript = []
        for idx, turn in enumerate(transcript):
            speaker = turn.get("speaker")
            if not speaker or speaker == "unknown":
                speaker = "Khách hàng"
            normalized_transcript.append({
                "index": idx,
                "speaker": speaker,
                "text": turn.get("text", ""),
                "start_seconds": turn.get("start_seconds"),
                "end_seconds": turn.get("end_seconds"),
            })

        reason = "Transcript quá ngắn hoặc thiếu ngữ cảnh nên hệ thống không đủ dữ liệu để tóm tắt, suy luận kết quả cuộc gọi hoặc chấm điểm nhân viên."
        metadata = self._analysis_metadata("insufficient_information")
        metadata["facts"] = {
            "customer_needs": [],
            "customer_pain_points": [],
            "agent_actions": [],
            "commitments": [],
            "outcome": {"status": "unclear", "description": reason, "evidence_turns": []},
            "important_moments": [],
        }

        return {
            "summary": ["Không đủ nội dung hội thoại để tạo tóm tắt đáng tin cậy."],
            "detailed_summary": {
                "overview": reason,
                "key_takeaways": ["Cần thêm nội dung hội thoại giữa Khách hàng và Nhân viên để phân tích chính xác."],
                "topics": [],
                "customer_needs": [],
                "customer_pain_points": [],
                "agent_actions": [],
                "outcome": "Chưa xác định do thiếu dữ liệu.",
                "next_steps": ["Gửi transcript đầy đủ hơn hoặc file ghi âm có đủ lượt trao đổi."],
                "action_items": [],
                "risks_or_escalations": [],
            },
            "sentiment": "neutral",
            "sentiment_reason": reason,
            "confidence": 0.0,
            "agent_score": None,
            "agent_score_breakdown": None,
            "quality_notes": ["Không chấm điểm nhân viên vì transcript không có đủ bằng chứng về tương tác hỗ trợ."],
            "agent_advice": ["Cần có thêm nội dung trao đổi thực tế trước khi đưa ra khuyến nghị cho nhân viên."],
            "analysis_metadata": metadata,
            "transcript": normalized_transcript,
        }

    def _sanitize_summary_result(self, data: dict, transcript: list[dict], facts: dict | None = None) -> dict:
        valid_indexes = self._valid_indexes(transcript)
        facts = facts or {}
        detailed = data.get("detailed_summary") if isinstance(data.get("detailed_summary"), dict) else {}
        summary = self._string_list(data.get("summary"), ["Không có tóm tắt cuộc gọi."], limit=5)
        summary = [item for item in summary if not self._looks_like_serialized_object(item)] or ["Không có tóm tắt cuộc gọi."]

        topics = []
        for item in self._dict_list(detailed.get("topics"), settings.max_summary_topics):
            topics.append({
                "title": self._text(item.get("title"), "Chủ đề chưa đặt tên", 120),
                "time_range": self._text(item.get("time_range"), "", 40),
                "details": self._string_list(item.get("details"), [], limit=5, max_len=240),
                "evidence_turns": self._evidence(item.get("evidence_turns"), valid_indexes),
            })

        action_items = []
        for item in self._dict_list(detailed.get("action_items"), settings.max_action_items):
            action_items.append({
                "owner": self._text(item.get("owner"), "Chưa xác định", 80),
                "task": self._text(item.get("task"), "", 240),
                "deadline": self._optional_text(item.get("deadline"), 80),
                "priority": self._priority(item.get("priority")),
                "evidence_turns": self._evidence(item.get("evidence_turns"), valid_indexes),
            })
        action_items = [item for item in action_items if item["task"]]

        fact_customer_needs = self._fact_texts(facts.get("customer_needs"))
        fact_pain_points = self._fact_texts(facts.get("customer_pain_points"))
        fact_agent_actions = self._fact_texts(facts.get("agent_actions"))
        outcome = self._text(detailed.get("outcome"), "", 400)
        if not outcome or self._looks_like_serialized_object(outcome):
            outcome = self._text((facts.get("outcome") or {}).get("description") if isinstance(facts.get("outcome"), dict) else None, "Chưa xác định kết quả cuối cuộc gọi.", 400)

        customer_needs = self._clean_text_list(
            self._string_list(detailed.get("customer_needs"), fact_customer_needs, limit=8, max_len=220),
            fact_customer_needs,
            limit=8,
        )
        customer_pain_points = self._clean_text_list(
            self._string_list(detailed.get("customer_pain_points"), fact_pain_points, limit=8, max_len=220),
            fact_pain_points,
            limit=8,
        )
        agent_actions = self._clean_text_list(
            self._string_list(detailed.get("agent_actions"), fact_agent_actions, limit=10, max_len=220),
            fact_agent_actions,
            limit=10,
        )

        return {
            "summary": summary,
            "detailed_summary": {
                "overview": self._text(detailed.get("overview"), "Chưa có tổng quan chi tiết.", 900),
                "key_takeaways": self._string_list(detailed.get("key_takeaways"), [], limit=7, max_len=240),
                "topics": topics,
                "customer_needs": customer_needs,
                "customer_pain_points": customer_pain_points,
                "agent_actions": agent_actions,
                "outcome": outcome,
                "next_steps": self._string_list(detailed.get("next_steps"), [], limit=8, max_len=220),
                "action_items": action_items,
                "risks_or_escalations": self._string_list(detailed.get("risks_or_escalations"), [], limit=8, max_len=220),
            },
        }

    def _sanitize_evaluation(self, data: dict, transcript: list[dict]) -> dict:
        sentiment = self._sentiment(data.get("sentiment"))
        breakdown = self._sanitize_score_breakdown(data.get("agent_score_breakdown"))
        computed_score = sum(item["score"] for item in breakdown.values())
        has_agent_turn = any(turn.get("speaker") == "Nhân viên" and turn.get("text") for turn in transcript)

        if not has_agent_turn:
            computed_score = 50 if sentiment == "negative" else 80
            breakdown = self._default_score_breakdown(computed_score, "Không có đủ lượt nói của Nhân viên nên dùng điểm mặc định theo sắc thái cuộc gọi.")
        elif computed_score <= 0:
            computed_score = self._int(data.get("agent_score"), 80, 0, 100)
            breakdown = self._default_score_breakdown(computed_score, "LLM không trả rubric hợp lệ nên hệ thống phân bổ điểm mặc định.")

        quality_notes = self._clean_text_list(
            self._string_list(data.get("quality_notes"), [], limit=8, max_len=260),
            [],
            limit=8,
        )
        agent_advice = [
            item for item in self._clean_text_list(
                self._string_list(data.get("agent_advice"), [], limit=4, max_len=260),
                [],
                limit=4,
            )
            if not self._is_irrelevant_advice(item)
        ]
        if not agent_advice:
            agent_advice = ["Đưa khuyến nghị cụ thể dựa trên điểm yếu quan sát được trong cuộc gọi, tránh dùng lời cảm ơn hoặc thông điệp quảng cáo không liên quan."]

        return {
            "sentiment": sentiment,
            "sentiment_reason": self._text(data.get("sentiment_reason"), "Không có lý do sắc thái cụ thể.", 1000),
            "confidence": self._float(data.get("confidence"), 0.8, 0.0, 1.0),
            "agent_score": self._int(computed_score, 80, 0, 100),
            "agent_score_breakdown": breakdown,
            "quality_notes": quality_notes,
            "agent_advice": agent_advice,
        }

    def _default_score_breakdown(self, score: int, reason: str) -> dict:
        score = self._int(score, 80, 0, 100)
        breakdown = {}
        total = 0
        keys = list(_SCORE_CRITERIA.keys())
        for key in keys:
            max_score = int(_SCORE_CRITERIA[key]["max"])
            item_score = self._int(round(max_score * score / 100), 0, 0, max_score)
            breakdown[key] = {
                "label": _SCORE_CRITERIA[key]["label"],
                "score": item_score,
                "max": max_score,
                "reason": reason,
            }
            total += item_score

        diff = score - total
        for key in keys:
            if diff == 0:
                break
            current = breakdown[key]["score"]
            max_score = breakdown[key]["max"]
            if diff > 0 and current < max_score:
                breakdown[key]["score"] += 1
                diff -= 1
            elif diff < 0 and current > 0:
                breakdown[key]["score"] -= 1
                diff += 1
        return breakdown

    def _sanitize_score_breakdown(self, value) -> dict:
        value = value if isinstance(value, dict) else {}
        breakdown = {}
        for key, config in _SCORE_CRITERIA.items():
            item = value.get(key) if isinstance(value.get(key), dict) else {}
            max_score = int(config["max"])
            breakdown[key] = {
                "label": config["label"],
                "score": self._int(item.get("score"), 0, 0, max_score),
                "max": max_score,
                "reason": self._text(item.get("reason"), "Chưa có nhận xét cho tiêu chí này.", 400),
            }
        return breakdown

    def _sanitize_fact_items(self, value, valid_indexes: set[int], limit: int) -> list[dict]:
        return [
            self._sanitize_fact_item(item, valid_indexes)
            for item in self._dict_list(value, limit)
        ]

    def _sanitize_fact_item(self, value, valid_indexes: set[int], default: dict | None = None) -> dict:
        value = value if isinstance(value, dict) else {}
        if not value and default is not None:
            value = default

        cleaned = {}
        for key, raw in value.items():
            if key == "evidence_turns":
                cleaned[key] = self._evidence(raw, valid_indexes)
            elif key == "deadline":
                cleaned[key] = self._optional_text(raw, 80)
            elif isinstance(raw, list):
                cleaned[key] = self._string_list(raw, [], limit=8, max_len=220)
            else:
                cleaned[key] = self._text(raw, "", 320)
        if "evidence_turns" not in cleaned:
            cleaned["evidence_turns"] = []
        return cleaned

    def _fact_texts(self, items) -> list[str]:
        texts = []
        source_items = items if isinstance(items, list) else []
        for item in source_items:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("description") or item.get("commitment")
            text = self._text(text, "", 240)
            if text and not self._looks_like_serialized_object(text):
                texts.append(text)
        return texts

    def _clean_text_list(self, value: list[str], fallback: list[str], limit: int) -> list[str]:
        cleaned = [item for item in value if item and not self._looks_like_serialized_object(item)]
        return (cleaned or fallback)[:limit]

    def _looks_like_serialized_object(self, value: str) -> bool:
        text = str(value or "").strip()
        return (
            (text.startswith("{") and text.endswith("}"))
            or (text.startswith("[") and text.endswith("]"))
            or "'owner':" in text
            or '"owner":' in text
            or "'status':" in text
            or '"status":' in text
        )

    def _is_irrelevant_advice(self, value: str) -> bool:
        text = str(value or "").strip().lower()
        blocked_phrases = [
            "thank you for listening",
            "podcast",
            "appreciate your business",
            "visit www",
            "toll-free",
        ]
        return any(phrase in text for phrase in blocked_phrases)

    def _format_transcript(self, transcript: list[dict]) -> str:
        lines = []
        for fallback_idx, turn in enumerate(transcript):
            idx = turn.get("index", fallback_idx)
            start = self._format_time(turn.get("start_seconds"))
            end = self._format_time(turn.get("end_seconds"))
            time_range = f" {start}-{end}" if start or end else ""
            lines.append(f"Index {idx}{time_range} | {turn.get('speaker', '')}: {turn.get('text', '')}")
        return "\n".join(lines)

    def _format_time(self, value) -> str:
        if value is None:
            return ""
        try:
            seconds = max(0, int(float(value)))
        except (TypeError, ValueError):
            return ""
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _parse_json_object(self, content: str) -> dict:
        content = content.strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            parsed = json.loads(content[start:end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON root must be an object")
        return parsed

    def _call_llm_json(self, base_url: str, prompt: str) -> dict:
        """
        Calls the LLM for a JSON object and repairs malformed JSON once.

        Local small models often follow the semantic task but produce syntax errors
        such as missing commas or prose around the object. Keep repair generic so all
        JSON-based prompts benefit without transcript-specific heuristics.
        """
        content = self._call_llm(base_url, prompt, json_mode=True)
        try:
            return self._parse_json_object(content)
        except Exception as parse_exc:
            logger.warning(f"LLM returned malformed JSON. Attempting one repair pass: {parse_exc}")

        repair_prompt = (
            "Bạn là bộ sửa định dạng JSON. Nhiệm vụ duy nhất: chuyển nội dung dưới đây thành MỘT JSON object hợp lệ.\n"
            "Quy tắc:\n"
            "- Không thêm thông tin mới.\n"
            "- Giữ nguyên ý nghĩa và các field đang có.\n"
            "- Sửa lỗi cú pháp như thiếu dấu phẩy, trailing comma, markdown fence, text ngoài JSON, hoặc value enum viết sai kiểu schema.\n"
            "- Nếu một giá trị không thể khôi phục chắc chắn, dùng null, mảng rỗng hoặc object rỗng phù hợp.\n"
            "- Trả về duy nhất JSON object hợp lệ, không giải thích.\n\n"
            f"Nội dung cần sửa:\n{content}"
        )
        repaired = self._call_llm(base_url, repair_prompt, json_mode=True)
        return self._parse_json_object(repaired)

    def _analysis_metadata(self, mode: str) -> dict:
        provider = self._last_provider or {}
        return {
            "summary_version": settings.llm_analysis_pipeline_version,
            "model_name": provider.get("model") or self._provider_summary(),
            "llm_provider": provider.get("name"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_mode": mode,
            "facts_prompt_version": "v1",
            "summary_prompt_version": "v1",
            "evaluation_prompt_version": "v1",
        }

    def _valid_indexes(self, transcript: list[dict]) -> set[int]:
        return {
            self._int(turn.get("index"), fallback_idx, 0, max(len(transcript) - 1, 0))
            for fallback_idx, turn in enumerate(transcript)
        }

    def _evidence(self, value, valid_indexes: set[int]) -> list[int]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            try:
                idx = int(item)
            except (TypeError, ValueError):
                continue
            if idx in valid_indexes and idx not in cleaned:
                cleaned.append(idx)
        return cleaned[:10]

    def _string_list(self, value, default: list[str], limit: int, max_len: int = 240) -> list[str]:
        if not isinstance(value, list):
            return default
        cleaned = [self._text(item, "", max_len) for item in value]
        cleaned = [item for item in cleaned if item]
        return cleaned[:limit] if cleaned else default

    def _dict_list(self, value, limit: int) -> list[dict]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)][:limit]

    def _sentiment(self, value) -> str:
        normalized = str(value or "").strip().lower()
        return normalized if normalized in {"positive", "neutral", "negative"} else "neutral"

    def _priority(self, value) -> str:
        normalized = str(value or "").strip().lower()
        return normalized if normalized in {"low", "medium", "high"} else "medium"

    def _text(self, value, default: str, max_len: int) -> str:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return text[:max_len]

    def _optional_text(self, value, max_len: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:max_len] if text else None

    def _int(self, value, default: int, min_value: int, max_value: int) -> int:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            parsed = default
        return max(min_value, min(max_value, parsed))

    def _float(self, value, default: float, min_value: float, max_value: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        return max(min_value, min(max_value, parsed))

    # ─────────────────────────────────────────────
    # Shared helpers
    # ─────────────────────────────────────────────
    def _get_base_url(self) -> str:
        providers = self._llm_providers()
        if not providers:
            logger.warning("No LLM provider configured. Analysis will fall back to deterministic defaults.")
            return "unconfigured"
        logger.info(
            "Configured LLM provider chain: "
            + " -> ".join(f"{provider['name']}({provider['model']} @ {provider['base_url']})" for provider in providers)
        )
        return "provider-chain"

    def _normalize_base_url(self, base_url: str) -> str:
        base_url = base_url.strip()
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            base_url = f"http://{base_url}"
        return base_url

    def _llm_providers(self) -> list[dict]:
        providers = []
        if settings.llm_api_base_url.strip() and settings.llm_api_model.strip():
            providers.append({
                "name": "LLM_API",
                "base_url": self._normalize_base_url(settings.llm_api_base_url),
                "model": settings.llm_api_model.strip(),
                "api_key": settings.llm_api_key.strip(),
            })
        if settings.llm_local_base_url.strip() and settings.llm_local_model.strip():
            providers.append({
                "name": "LLM_LOCAL",
                "base_url": self._normalize_base_url(settings.llm_local_base_url),
                "model": settings.llm_local_model.strip(),
                "api_key": settings.llm_local_api_key.strip(),
            })
        if not providers and settings.llm_base_url.strip() and settings.llm_model.strip():
            providers.append({
                "name": "LLM_LEGACY",
                "base_url": self._normalize_base_url(settings.llm_base_url),
                "model": settings.llm_model.strip(),
                "api_key": settings.llm_api_key.strip(),
            })
        return providers

    def _provider_summary(self) -> str:
        providers = self._llm_providers()
        return " -> ".join(provider["model"] for provider in providers) if providers else "unconfigured"

    def _call_llm(self, base_url: str, prompt: str, json_mode: bool = False) -> str:
        """
        Calls configured OpenAI-compatible LLM providers and returns the raw text
        content of the first successful assistant reply.
        """
        providers = self._llm_providers()
        if not providers:
            raise RuntimeError("No LLM provider configured. Set LLM_API_* or LLM_LOCAL_* variables.")

        errors = []
        for idx, provider in enumerate(providers):
            try:
                return self._call_llm_provider(provider, prompt, json_mode=json_mode)
            except RuntimeError as exc:
                errors.append(f"{provider['name']}: {exc}")
                next_provider = providers[idx + 1]["name"] if idx + 1 < len(providers) else None
                if next_provider:
                    logger.error(
                        f"{provider['name']} provider failed. Falling back to {next_provider}. "
                        f"Reason: {exc}"
                    )
                else:
                    logger.error(f"{provider['name']} provider failed and no fallback provider remains. Reason: {exc}")

        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))

    def _call_llm_provider(self, provider: dict, prompt: str, json_mode: bool = False) -> str:
        payload = {
            "model": provider["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Bạn là hệ thống QA cuộc gọi chăm sóc khách hàng. "
                        "Luôn trả lời bằng tiếng Việt tự nhiên. "
                        "Chỉ dùng JSON hợp lệ khi người dùng yêu cầu JSON. "
                        "Không bịa thông tin ngoài transcript và không dùng intro/outro quảng cáo làm nội dung phân tích."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {}
        if provider["api_key"]:
            headers["Authorization"] = f"Bearer {provider['api_key']}"

        url = f"{provider['base_url'].rstrip('/')}/chat/completions"
        logger.info(
            f"Calling {provider['name']} provider: endpoint={provider['base_url']} "
            f"model={provider['model']} timeout={settings.llm_api_timeout_seconds}s"
        )
        try:
            with httpx.Client(timeout=settings.llm_api_timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                if json_mode and response.status_code in {400, 404, 422}:
                    logger.warning(
                        f"{provider['name']} provider rejected response_format=json_object. "
                        "Retrying the same prompt without JSON mode."
                    )
                    payload.pop("response_format", None)
                    response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"].strip()
            self._last_provider = provider
            logger.info(f"Successfully received response from {provider['name']} model.")

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
            if isinstance(http_exc, httpx.TimeoutException):
                logger.error(
                    f"{provider['name']} provider timed out after "
                    f"{settings.llm_api_timeout_seconds}s: {str(http_exc)}"
                )
                raise RuntimeError(f"timed out after {settings.llm_api_timeout_seconds}s") from http_exc
            logger.error(f"{provider['name']} provider HTTP request failed: {str(http_exc)}")
            raise RuntimeError(f"HTTP call failed: {str(http_exc)}") from http_exc
        except json.JSONDecodeError as json_exc:
            logger.error(f"Failed to parse {provider['name']} provider HTTP response as JSON.")
            raise RuntimeError(f"Invalid JSON returned from LLM: {str(json_exc)}") from json_exc
        except Exception as exc:
            logger.error(f"Unexpected error during {provider['name']} provider call: {str(exc)}")
            raise RuntimeError(str(exc)) from exc
