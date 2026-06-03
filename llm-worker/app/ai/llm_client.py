import json
import logging
import re
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
            role_response = self._call_llm(base_url, role_map_prompt)
            parsed = json.loads(role_response)

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
            "QUY TẮC ĐÁNH GIÁ ĐIỂM NHÂN VIÊN (agent_score - Thang điểm 100):\n"
            "- agent_score đại diện cho CHẤT LƯỢNG HỖ TRỢ của Nhân viên, chứ không phải tâm trạng của Khách hàng.\n"
            "- Nếu cuộc gọi quá ngắn hoặc KHÔNG CÓ bất kỳ lượt nói nào của Nhân viên (chỉ có Khách hàng nói một mình):\n"
            "  * Gán điểm mặc định là 80 nếu sắc thái cuộc gọi là Tích cực hoặc Trung lập (chưa thể hiện lỗi gì của nhân viên).\n"
            "  * Gán điểm mặc định là 50 nếu sắc thái cuộc gọi là Tiêu cực (nhắc nhở nhân viên cần chủ động phản hồi xoa dịu khách), tuyệt đối KHÔNG được đánh giá 0 hoặc 100 điểm một cách tùy tiện.\n"
            "- Nếu cuộc gọi có đầy đủ tương tác:\n"
            "  * Sắc thái Trung lập (Neutral): Điểm nhân viên nên nằm trong khoảng 70 - 85, trừ khi nhân viên làm việc xuất sắc (90+) hoặc tệ hại (dưới 50). Không cho 0 hay 100 điểm một cách vô lý.\n"
            "  * Sắc thái Tiêu cực (Negative): Nếu khách hàng giận dữ về sản phẩm nhưng Nhân viên vẫn lịch sự, bình tĩnh hỗ trợ đúng quy trình, điểm của nhân viên vẫn phải ở mức Khá (70 - 85). Không đánh giá 0 điểm trừ khi nhân viên thô lỗ, cãi cọ hoặc phớt lờ khách hàng.\n"
            "  * Sắc thái Tích cực (Positive): Điểm nhân viên xứng đáng ở mức 80 - 100.\n\n"
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
            "QUY TẮC ĐÁNH GIÁ ĐIỂM NHÂN VIÊN (agent_score - Thang điểm 100):\n"
            "- agent_score đại diện cho CHẤT LƯỢNG HỖ TRỢ của Nhân viên, chứ không phải tâm trạng của Khách hàng.\n"
            "- Nếu cuộc gọi quá ngắn hoặc KHÔNG CÓ bất kỳ lượt nói nào của Nhân viên (chỉ có Khách hàng nói một mình):\n"
            "  * Gán điểm mặc định là 80 nếu sắc thái cuộc gọi là Tích cực hoặc Trung lập (chưa thể hiện lỗi gì của nhân viên).\n"
            "  * Gán điểm mặc định là 50 nếu sắc thái cuộc gọi là Tiêu cực (nhắc nhở nhân viên cần chủ động phản hồi xoa dịu khách), tuyệt đối KHÔNG được đánh giá 0 hoặc 100 điểm một cách tùy tiện.\n"
            "- Nếu cuộc gọi có đầy đủ tương tác:\n"
            "  * Sắc thái Trung lập (Neutral): Điểm nhân viên nên nằm trong khoảng 70 - 85, trừ khi nhân viên làm việc xuất sắc (90+) hoặc tệ hại (dưới 50). Không cho 0 hay 100 điểm một cách vô lý.\n"
            "  * Sắc thái Tiêu cực (Negative): Nếu khách hàng giận dữ về sản phẩm nhưng Nhân viên vẫn lịch sự, bình tĩnh hỗ trợ đúng quy trình, điểm của nhân viên vẫn phải ở mức Khá (70 - 85). Không đánh giá 0 điểm trừ khi nhân viên thô lỗ, cãi cọ hoặc phớt lờ khách hàng.\n"
            "  * Sắc thái Tích cực (Positive): Điểm nhân viên xứng đáng ở mức 80 - 100.\n\n"
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
            with httpx.Client(timeout=300) as client:
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
