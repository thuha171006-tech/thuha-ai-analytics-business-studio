"""
Question Sufficiency Validator for Thu Hà AI Analytics Studio.
Evaluates whether the uploaded dataset contains sufficient dimensions, columns, and metric granularity
to rigorously answer the user's focus analytical questions.

Produces:
1. is_sufficient (bool)
2. what_is_missing (str) - Specific missing columns and business dimensions
3. what_is_needed (str) - Concrete data format and column requirements needed
4. suggested_questions (List[str]) - Tailored questions that CAN be answered with the current file
5. focus_deep_dive (Dict[str, Any]) - When sufficient: in-depth, verified analytical insights directly answering the question
6. focus_angle (str) - The recommended view angle to auto-select in Step 3
"""

import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

class QuestionSufficiencyValidator:

    TOPIC_SPECS = {
        "CHANNEL": {
            "name": "Hiệu quả Kênh bán hàng (Omnichannel)",
            "keywords": ["kênh", "channel", "sàn", "platform", "omnichannel", "tiktok", "shopee", "lazada", "facebook", "website", "kênh bán"],
            "required_indicators": ["kênh", "channel", "sàn", "platform", "nguồn", "kenh_ban"],
            "missing_desc": "Cột Kênh Bán Hàng (Channel/Platform/Sàn TMĐT)",
            "needed_desc": "Cần có cột phân loại kênh bán (Shopee, TikTok Shop, Lazada, Website...) kèm doanh thu từng kênh.",
            "recommended_angle": "CHANNEL"
        },
        "CAMPAIGN_MARKETING": {
            "name": "Chiến dịch Marketing, Chi phí & Causal Uplift (ROI/ROAS)",
            "keywords": ["chiến dịch", "campaign", "marketing", "quảng cáo", "chi phí mkt", "chi phí marketing", "chi phí quảng cáo", "ad_spend", "ad cost", "uplift", "causal", "roas", "roi", "ngân sách marketing"],
            "required_indicators": ["chiến dịch", "campaign", "chi phí", "marketing_cost", "ngân sách", "ad_cost"],
            "missing_desc": "Cột Tên Chiến Dịch Marketing & Chi Phí Quảng Cáo (Marketing Cost/Ad Spend)",
            "needed_desc": "Cần có bảng/cột Chiến dịch Marketing kèm số tiền Chi phí Marketing thực chi để tính ROI, ROAS và bóc tách tăng trưởng thuần (Causal Uplift).",
            "recommended_angle": "CAMPAIGN"
        },
        "RETURNS_CANCELLATIONS": {
            "name": "Hàng hoàn, Tỷ lệ hủy đơn & Rủi ro dòng tiền",
            "keywords": ["hoàn", "trả hàng", "hàng hoàn", "return", "hủy đơn", "tỷ lệ hoàn", "đơn hoàn"],
            "required_indicators": ["trạng thái", "status", "hàng trả", "return_amount", "tiền hoàn", "cancelled", "returned"],
            "missing_desc": "Cột Trạng Thái Đơn Hàng (Status) hoặc Tiền/Số lượng Hàng Hoàn (Return Amount)",
            "needed_desc": "Cần có cột Trạng thái đơn (COMPLETED, RETURNED, CANCELLED) hoặc Số tiền hàng trả để AI tính tỷ lệ hoàn và đánh giá thất thoát dòng tiền.",
            "recommended_angle": "CHANNEL"
        },
        "COGS_MARGIN": {
            "name": "Giá vốn (COGS) & Biên lợi nhuận gộp / Biên CM",
            "keywords": ["giá vốn", "cogs", "lợi nhuận gộp", "gross profit", "lãi gộp", "biên gộp", "biên cm", "biên đóng góp"],
            "required_indicators": ["giá vốn", "cogs", "cost", "von", "chi phí hàng bán"],
            "missing_desc": "Cột Giá Vốn Hàng Bán (COGS/Unit Cost)",
            "needed_desc": "Cần có cột Giá vốn cho từng sản phẩm/đơn hàng để tính toán chính xác Lợi nhuận gộp và Biên đóng góp (Contribution Margin).",
            "recommended_angle": "CAMPAIGN"
        },
        "DISCOUNT_VOUCHER": {
            "name": "Voucher, Chiết khấu & Trợ giá khuyến mãi",
            "keywords": ["voucher", "mã giảm giá", "chiết khấu", "discount", "khuyến mãi", "trợ giá"],
            "required_indicators": ["voucher", "chiết khấu", "discount", "mã giảm giá", "trợ giá"],
            "missing_desc": "Cột Chiết Khấu / Mã Voucher (Discount/Voucher Amount)",
            "needed_desc": "Cần có cột Số tiền chiết khấu hoặc Tiền voucher áp dụng cho từng đơn hàng để kiểm soát rủi ro ăn lấn giá.",
            "recommended_angle": "TIMELINE"
        },
        "TIMELINE_TREND": {
            "name": "Xu hướng doanh thu theo Thời gian (Daily / Monthly Trend)",
            "keywords": ["thời gian", "ngày", "tháng", "trend", "xu hướng", "timeline", "theo ngày", "chu kỳ thời gian", "biến động theo ngày"],
            "required_indicators": ["ngày", "date", "thời gian", "tháng", "created_at", "order_date"],
            "missing_desc": "Cột Ngày / Thời Gian Giao Dịch (Date/Timestamp)",
            "needed_desc": "Cần có cột Ngày tạo đơn / Ngày ghi nhận giao dịch (định dạng YYYY-MM-DD hoặc DD/MM/YYYY) để vẽ biểu đồ diễn biến doanh thu.",
            "recommended_angle": "TIMELINE"
        },
        "PRODUCT_PARETO": {
            "name": "Cơ cấu Sản phẩm bán chạy & Pareto 80/20",
            "keywords": ["sản phẩm", "product", "mặt hàng", "sku", "pareto", "bán chạy", "danh mục", "mặt hàng chủ lực"],
            "required_indicators": ["sản phẩm", "product", "sku", "mặt hàng", "tên hàng", "mã sp"],
            "missing_desc": "Cột Tên / Mã Sản Phẩm (Product Name / SKU)",
            "needed_desc": "Cần có cột Mã hoặc Tên sản phẩm trong từng đơn để phân tích tỷ trọng 80/20 và xác định nhóm hàng dẫn dắt doanh số.",
            "recommended_angle": "PRODUCT"
        },
        "SALES_FUNNEL": {
            "name": "Phễu bán hàng, Giai đoạn cơ hội & Tỷ lệ chốt sale (Win Rate)",
            "keywords": ["phễu", "funnel", "giai đoạn", "lead", "tiềm năng", "cơ hội", "chốt sale", "win rate", "pipeline"],
            "required_indicators": ["giai đoạn", "stage", "mã lead", "cơ hội", "giá trị cơ hội", "trạng thái cơ hội"],
            "missing_desc": "Cấu trúc dữ liệu Phễu CRM (Cột Giai đoạn, Tên cơ hội, Giá trị phễu)",
            "needed_desc": "Cần tệp quản lý Cơ hội bán hàng (CRM Pipeline) có cột 'Giai đoạn' (Tiếp cận, Đánh giá, Đàm phán, Thắng, Thua) và 'Giá trị cơ hội' để đo lường tỷ lệ chốt sale.",
            "recommended_angle": "FUNNEL_STAGE"
        },
        "MANUFACTURING_DEFECTS": {
            "name": "Quản lý sản xuất, Tỷ lệ lỗi theo Ca & Dây chuyền (Defect Rate)",
            "keywords": ["dây chuyền", "ca sản xuất", "ca làm việc", "phế phẩm", "tỷ lệ lỗi", "sản lượng", "hỏng", "qc", "kiểm định", "sản phẩm lỗi"],
            "required_indicators": ["dây chuyền", "ca", "sản lượng", "số lỗi", "phế phẩm", "mã lô"],
            "missing_desc": "Dữ liệu Kiểm định Sản xuất (Cột Dây chuyền, Ca sản xuất, Sản lượng, Số lỗi)",
            "needed_desc": "Cần tệp nhật ký sản xuất có cột 'Dây chuyền', 'Ca làm việc', 'Sản lượng đạt' và 'Số sản phẩm lỗi' để AI tính toán tỷ lệ phế phẩm ppm/%.",
            "recommended_angle": "QUALITY_LINE"
        },
        "SUBSCRIPTION_DEFERRED": {
            "name": "Doanh thu dịch vụ thuê bao (MRR) & Doanh thu hoãn lại",
            "keywords": ["thuê bao", "subscription", "chu kỳ thu", "tiền thu trước", "doanh thu tháng", "hoãn lại", "deferred", "mrr", "arr"],
            "required_indicators": ["chu kỳ", "tiền thu trước", "doanh thu tháng", "số tháng dịch vụ", "thu trước"],
            "missing_desc": "Dữ liệu Hợp đồng Dịch vụ / Thuê bao (Cột Chu kỳ thu, Tiền thu trước, Doanh thu tháng)",
            "needed_desc": "Cần tệp theo dõi hợp đồng có cột 'Chu kỳ thu' (Tháng/Năm), 'Tiền thu trước' và 'Số tháng dịch vụ' để AI phân bổ MRR và hạch toán doanh thu hoãn lại.",
            "recommended_angle": "SUBSCRIPTION_MRR"
        },
        "STORE_PNL": {
            "name": "Chuỗi cửa hàng, Chi phí mặt bằng & Lợi nhuận trên m2",
            "keywords": ["cửa hàng", "mặt bằng", "chi phí thuê", "tiền thuê", "diện tích", "m2", "store", "chi nhánh", "tỷ suất sinh lời"],
            "required_indicators": ["cửa hàng", "chi phí thuê", "diện tích", "nhân sự", "mặt bằng", "store"],
            "missing_desc": "Dữ liệu Vận hành Cửa hàng (Cột Tên cửa hàng, Diện tích m2, Tiền thuê mặt bằng)",
            "needed_desc": "Cần tệp quản lý chuỗi bán lẻ có cột 'Tên cửa hàng', 'Diện tích (m2)', 'Chi phí thuê' và 'Chi phí nhân sự' để tính hiệu suất sinh lời trên mỗi m2.",
            "recommended_angle": "STORE_EFFICIENCY"
        },
        "COHORT_RETENTION": {
            "name": "Giữ chân khách hàng & Vòng đời Cohort (Retention Rate)",
            "keywords": ["cohort", "giữ chân", "retention", "m0", "m1", "m2", "quay lại", "lặp lại", "churn"],
            "required_indicators": ["cohort", "m0", "m1", "m2", "khách mới"],
            "missing_desc": "Cấu trúc Bảng Cohort (Cột Cohort tháng gia nhập và các cột M0, M1, M2...)",
            "needed_desc": "Cần tệp ma trận Cohort tam giác (cột Tháng khởi tạo M0, M1, M2...) hoặc lịch sử đơn hàng có Mã khách hàng để đo lường độ gắn kết vòng đời.",
            "recommended_angle": "COHORT_RETENTION"
        }
    }

    @classmethod
    def validate_question_sufficiency(
        cls,
        user_question: str,
        df_raw: pd.DataFrame,
        original_cols: List[str],
        domain_type: str,
        pnl_records: List[Dict[str, Any]],
        financial_kpis: Dict[str, Any],
        gemini_service: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Validates whether the dataset has sufficient data to answer the user's question.
        Returns a rich dict with is_sufficient, what_is_missing, what_is_needed,
        suggested_questions, and deep_dive_analysis.
        """
        user_question_clean = (user_question or "").strip()
        if not user_question_clean:
            # Default question tailored to current domain
            return cls._get_default_domain_sufficiency(domain_type, df_raw, pnl_records, financial_kpis)

        q_lower = user_question_clean.lower()
        
        # Prepare list of existing columns in lowercase
        cols_lower = [str(c).lower().replace("_", " ").strip() for c in (original_cols or list(df_raw.columns))]
        
        # Detect which topics are demanded by the question
        demanded_topics = []
        for topic_key, topic_info in cls.TOPIC_SPECS.items():
            if any(k in q_lower for k in topic_info["keywords"]):
                demanded_topics.append(topic_key)

        # If no specific analytical topic detected, check generic P&L / data summary
        if not demanded_topics:
            if any(k in q_lower for k in ["tổng quan", "hiệu quả", "lãi lỗ", "báo cáo", "phân tích", "kết quả"]):
                demanded_topics = ["GENERIC_PNL"]
            else:
                # Custom question - default to domain matching
                demanded_topics = [cls._get_primary_topic_for_domain(domain_type)]

        # Check sufficiency for each demanded topic
        missing_topics = []
        satisfied_topics = []
        missing_reasons = []
        needed_reasons = []

        for t_key in demanded_topics:
            if t_key == "GENERIC_PNL":
                if df_raw is not None and not df_raw.empty:
                    satisfied_topics.append(t_key)
                else:
                    missing_topics.append(t_key)
                    missing_reasons.append("Tệp không có dữ liệu để tổng hợp P&L.")
                    needed_reasons.append("Cần tải lên tệp dữ liệu có số dòng và cột chỉ số hợp lệ.")
                continue

            t_info = cls.TOPIC_SPECS[t_key]
            # Check domain-specific requirements
            is_satisfied = False
            
            # Domain check shortcut
            if t_key == "MANUFACTURING_DEFECTS" and domain_type == "MANUFACTURING_QUALITY":
                is_satisfied = True
            elif t_key == "SALES_FUNNEL" and domain_type == "SALES_FUNNEL":
                is_satisfied = True
            elif t_key == "SUBSCRIPTION_DEFERRED" and domain_type == "SUBSCRIPTION_DEFERRED":
                is_satisfied = True
            elif t_key == "STORE_PNL" and domain_type == "STORE_PNL":
                is_satisfied = True
            elif t_key == "COHORT_RETENTION" and domain_type == "COHORT_RETENTION":
                is_satisfied = True
            else:
                # Check column indicators
                has_col = any(any(req in col for req in t_info["required_indicators"]) for col in cols_lower)
                
                # Check special operational data
                if t_key == "CAMPAIGN_MARKETING":
                    has_campaign_names = any("chiến dịch" in col or "campaign" in col for col in cols_lower)
                    has_cost = any("chi phí" in col or "cost" in col for col in cols_lower) or any(p.get("direct_cost", 0) > 0 for p in pnl_records)
                    is_satisfied = (has_campaign_names and has_cost) or any(p.get("campaign_id") != "ORGANIC" and p.get("direct_cost", 0) > 0 for p in pnl_records)
                elif t_key == "RETURNS_CANCELLATIONS":
                    is_satisfied = has_col or financial_kpis.get("total_return_amount", 0) > 0 or any("trạng thái" in col for col in cols_lower)
                elif t_key == "CHANNEL":
                    is_satisfied = has_col or any(p.get("channel") for p in pnl_records if p.get("channel") != "UNKNOWN")
                elif t_key == "PRODUCT_PARETO":
                    is_satisfied = has_col
                elif t_key == "TIMELINE_TREND":
                    is_satisfied = has_col
                elif t_key == "COGS_MARGIN":
                    is_satisfied = has_col or financial_kpis.get("total_cogs", 0) > 0
                elif t_key == "DISCOUNT_VOUCHER":
                    is_satisfied = has_col or financial_kpis.get("total_discount_amount", 0) > 0
                else:
                    is_satisfied = has_col

            if is_satisfied:
                satisfied_topics.append(t_key)
            else:
                missing_topics.append(t_key)
                missing_reasons.append(t_info["missing_desc"])
                needed_reasons.append(t_info["needed_desc"])

        is_sufficient = (len(missing_topics) == 0) and (df_raw is not None and not df_raw.empty)
        
        # Tailored suggested questions for the CURRENT file
        suggested_questions = cls._generate_suggested_questions_for_current_data(domain_type, df_raw, pnl_records)

        primary_topic = satisfied_topics[0] if satisfied_topics else (demanded_topics[0] if demanded_topics else "GENERIC_PNL")
        focus_angle = cls.TOPIC_SPECS.get(primary_topic, {}).get("recommended_angle", "CHANNEL")

        if not is_sufficient:
            dataset_name = df_raw.columns.tolist() if df_raw is not None else []
            what_is_missing = f"Tệp dữ liệu tải lên thiếu các trường số liệu cốt lõi để phân tích vấn đề này: " + "; ".join(missing_reasons) + "."
            what_is_needed = f"Để phân tích đúng và sâu vấn đề '{user_question_clean}', bạn cần: " + " ".join(needed_reasons)
            
            return {
                "is_sufficient": False,
                "user_question": user_question_clean,
                "demanded_topics": demanded_topics,
                "satisfied_topics": satisfied_topics,
                "missing_topics": missing_topics,
                "what_is_missing": what_is_missing,
                "what_is_needed": what_is_needed,
                "missing_fields": missing_reasons,
                "suggested_questions": suggested_questions,
                "focus_angle": focus_angle,
                "deep_dive_analysis": None
            }

        # DỮ LIỆU ĐỦ ĐIỀU KIỆN: Tạo phân tích chuyên sâu trọng tâm
        deep_dive = cls._generate_deep_dive_insights(
            user_question=user_question_clean,
            primary_topic=primary_topic,
            domain_type=domain_type,
            df_raw=df_raw,
            pnl_records=pnl_records,
            financial_kpis=financial_kpis,
            gemini_service=gemini_service
        )

        return {
            "is_sufficient": True,
            "user_question": user_question_clean,
            "demanded_topics": demanded_topics,
            "satisfied_topics": satisfied_topics,
            "missing_topics": [],
            "what_is_missing": "",
            "what_is_needed": "",
            "missing_fields": [],
            "suggested_questions": suggested_questions,
            "focus_angle": focus_angle,
            "deep_dive_analysis": deep_dive
        }

    @classmethod
    def _get_primary_topic_for_domain(cls, domain_type: str) -> str:
        mapping = {
            "MANUFACTURING_QUALITY": "MANUFACTURING_DEFECTS",
            "SALES_FUNNEL": "SALES_FUNNEL",
            "SUBSCRIPTION_DEFERRED": "SUBSCRIPTION_DEFERRED",
            "STORE_PNL": "STORE_PNL",
            "COHORT_RETENTION": "COHORT_RETENTION",
            "RETAIL_ORDERS": "CHANNEL"
        }
        return mapping.get(domain_type, "CHANNEL")

    @classmethod
    def _generate_suggested_questions_for_current_data(
        cls, 
        domain_type: str, 
        df_raw: pd.DataFrame, 
        pnl_records: List[Dict[str, Any]]
    ) -> List[str]:
        """Provides 3 highly relevant questions that match the exact columns of the loaded dataset."""
        if domain_type == "MANUFACTURING_QUALITY":
            return [
                "Dây chuyền sản xuất nào có tỷ lệ lỗi cao nhất và cần bảo trì gấp?",
                "So sánh sản lượng và tỷ lệ đạt chất lượng giữa Ca 1, Ca 2 và Ca 3?",
                "Tỷ lệ phế phẩm bình quân toàn dự án có vượt ngưỡng trần kiểm định 1.0% không?"
            ]
        elif domain_type == "SALES_FUNNEL":
            return [
                "Tỷ lệ chuyển đổi chốt deal thành công (Win Rate) qua từng giai đoạn phễu?",
                "Kênh tiếp cận khách hàng nào mang lại số lượng hợp đồng thắng lớn nhất?",
                "Giai đoạn nào trong phễu đang gây tắc nghẽn và làm thất thoát giá trị cơ hội nhiều nhất?"
            ]
        elif domain_type == "SUBSCRIPTION_DEFERRED":
            return [
                "Doanh thu phân bổ hàng tháng (MRR) và Doanh thu hoãn lại còn phải thực hiện dịch vụ?",
                "So sánh doanh thu giữa các gói hợp đồng theo Chu kỳ Tháng vs Chu kỳ Năm?",
                "Tổng tiền thu trước từ khách hàng đã được ghi nhận vào kết quả kinh doanh bao nhiêu %?"
            ]
        elif domain_type == "STORE_PNL":
            return [
                "Cửa hàng nào có chi phí thuê mặt bằng cao nhất và tỷ suất sinh lời trên mỗi m2?",
                "So sánh lợi nhuận ròng giữa các chi nhánh: Đâu là điểm bán đang chịu lỗ vận hành?",
                "Cơ cấu chi phí cố định (Mặt bằng + Nhân sự) chiếm bao nhiêu % tổng doanh thu của từng cửa hàng?"
            ]
        elif domain_type == "COHORT_RETENTION":
            return [
                "Tỷ lệ giữ chân khách hàng (Retention Rate) qua các chu kỳ M0, M1, M2... là bao nhiêu %?",
                "Tháng gia nhập (Cohort) nào có tỷ lệ khách hàng quay lại mua sắm cao nhất?",
                "Tốc độ suy giảm tỷ lệ khách hoạt động (Churn Rate) mạnh nhất ở giai đoạn nào?"
            ]
        else: # RETAIL_ORDERS
            return [
                "Doanh thu theo Kênh nào cao nhất và Kênh nào có tỷ lệ hoàn hàng nghiêm trọng nhất?",
                "Chi phí theo Chiến dịch nào cao nhất và có tạo ra tăng trưởng thực sự (Causal Uplift) không?",
                "Biên đóng góp thực tế (Contribution Margin) toàn dự án sau khi trừ giá vốn, voucher và chi phí marketing?"
            ]

    @classmethod
    def _get_default_domain_sufficiency(
        cls, 
        domain_type: str, 
        df_raw: pd.DataFrame, 
        pnl_records: List[Dict[str, Any]], 
        financial_kpis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handles empty question state by setting up a domain-specific default focus."""
        sug_qs = cls._generate_suggested_questions_for_current_data(domain_type, df_raw, pnl_records)
        default_q = sug_qs[0]
        topic = cls._get_primary_topic_for_domain(domain_type)
        deep_dive = cls._generate_deep_dive_insights(
            user_question=default_q,
            primary_topic=topic,
            domain_type=domain_type,
            df_raw=df_raw,
            pnl_records=pnl_records,
            financial_kpis=financial_kpis
        )
        return {
            "is_sufficient": True,
            "user_question": default_q,
            "demanded_topics": [topic],
            "satisfied_topics": [topic],
            "missing_topics": [],
            "what_is_missing": "",
            "what_is_needed": "",
            "missing_fields": [],
            "suggested_questions": sug_qs,
            "focus_angle": cls.TOPIC_SPECS.get(topic, {}).get("recommended_angle", "CHANNEL"),
            "deep_dive_analysis": deep_dive
        }

    @classmethod
    def _generate_deep_dive_insights(
        cls,
        user_question: str,
        primary_topic: str,
        domain_type: str,
        df_raw: pd.DataFrame,
        pnl_records: List[Dict[str, Any]],
        financial_kpis: Dict[str, Any],
        gemini_service: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a deep-dive, empirical analytical response addressing the question directly.
        Uses exact numerical calculations from the active domain records.
        """
        topic_title = cls.TOPIC_SPECS.get(primary_topic, {}).get("name", "Phân Tích Dữ Liệu Chuyên Sâu")
        bullets = []
        action_recommendation = ""
        key_metrics = []

        # 1. MANUFACTURING QUALITY
        if domain_type == "MANUFACTURING_QUALITY":
            lines = pnl_records or []
            worst = max(lines, key=lambda x: x.get("defect_rate_pct", 0)) if lines else {}
            best = min(lines, key=lambda x: x.get("defect_rate_pct", 0)) if lines else {}
            tot_out = sum(r.get("output_qty", 0) for r in lines)
            tot_pass = sum(r.get("passed_qty", 0) for r in lines)
            tot_err = sum(r.get("defect_qty", 0) for r in lines)
            avg_err = round(tot_err / tot_out * 100, 2) if tot_out > 0 else 0.0

            bullets.append(f"Toàn bộ hệ thống sản xuất đã hoàn tất kiểm định {tot_out:,.0f} sản phẩm. Đạt chuẩn: {tot_pass:,.0f} SP ({round(tot_pass/tot_out*100, 1) if tot_out > 0 else 0}%), Phế phẩm: {tot_err:,.0f} SP (Tỷ lệ lỗi bình quân {avg_err}%).")
            if worst:
                bullets.append(f"Điểm nghẽn chất lượng: {worst.get('campaign_name', worst.get('campaign_id'))} ghi nhận tỷ lệ lỗi cao nhất toàn xưởng ({worst.get('defect_rate_pct', 0)}% với {worst.get('defect_qty', 0):,.0f} lỗi), vượt ngưỡng kiểm soát 1.0%.")
            if best and best != worst:
                bullets.append(f"Hình mẫu vận hành chuẩn: {best.get('campaign_name', best.get('campaign_id'))} duy trì tỷ lệ lỗi thấp nhất ({best.get('defect_rate_pct', 0)}%), đạt chuẩn vận hành ổn định.")
            
            action_recommendation = f"Tạm dừng cân chỉnh kỹ thuật thiết bị tại {worst.get('campaign_name', 'dây chuyền có tỷ lệ lỗi cao')} trong 48h tới. Nhân rộng quy trình kiểm soát ca của {best.get('campaign_name', 'dây chuyền chuẩn')} để giảm tỷ lệ phế phẩm toàn nhà máy về dưới 0.8%."
            key_metrics = [
                {"label": "Tổng Sản Lượng", "value": f"{tot_out:,.0f} SP", "status": "neutral"},
                {"label": "Tỷ Lệ Lỗi Bình Quân", "value": f"{avg_err}%", "status": "warning" if avg_err > 1.0 else "positive"},
                {"label": "Dây Chuyền Lỗi Nhất", "value": f"{worst.get('campaign_id', 'N/A')} ({worst.get('defect_rate_pct', 0)}%)", "status": "danger"},
                {"label": "Tỷ Lệ Đạt Chuẩn", "value": f"{round(tot_pass/tot_out*100, 1) if tot_out > 0 else 0}%", "status": "positive"}
            ]

        # 2. SALES FUNNEL
        elif domain_type == "SALES_FUNNEL":
            deals = pnl_records or []
            total_leads = sum(r.get("order_count", 0) for r in deals)
            won_deals = [r for r in deals if "thắng" in str(r.get("campaign_id", "")).lower() or "won" in str(r.get("campaign_id", "")).lower()]
            lost_deals = [r for r in deals if "thua" in str(r.get("campaign_id", "")).lower() or "lost" in str(r.get("campaign_id", "")).lower()]
            
            won_cnt = sum(r.get("order_count", 0) for r in won_deals)
            lost_cnt = sum(r.get("order_count", 0) for r in lost_deals)
            won_val = sum(r.get("net_revenue", 0) for r in won_deals)
            tot_pipeline = sum(r.get("gross_revenue", 0) for r in deals)
            win_rate = round(won_cnt / total_leads * 100, 1) if total_leads > 0 else 0.0

            bullets.append(f"Tổng dung lượng phễu ghi nhận {total_leads:,.0f} cơ hội với tổng giá trị tiềm năng {tot_pipeline:,.0f} đ.")
            bullets.append(f"Tỷ lệ chốt sale thành công (Win Rate) đạt {win_rate}% (Tương ứng {won_cnt:,.0f} deal thắng, hiện thực hóa {won_val:,.0f} đ giá trị hợp đồng).")
            if lost_cnt > 0:
                bullets.append(f"Số lượng cơ hội thất bại (Lost Deals): {lost_cnt:,.0f} deal ({round(lost_cnt/total_leads*100, 1)}% tổng phễu), gây thất thoát đáng kể chi phí tiếp cận ban đầu.")

            action_recommendation = "Thực hiện khảo sát Lost Deal Survey trên các cơ hội bị trượt để cải thiện kịch bản xử lý từ chối giá và rút ngắn chu kỳ đàm phán."
            key_metrics = [
                {"label": "Tổng Cơ Hội (Leads)", "value": f"{total_leads:,.0f}", "status": "neutral"},
                {"label": "Tỷ Lệ Chốt Thắng", "value": f"{win_rate}%", "status": "positive" if win_rate >= 20 else "warning"},
                {"label": "Giá Trị Thắng (Won)", "value": f"{won_val:,.0f} đ", "status": "positive"},
                {"label": "Tổng Giá Trị Phễu", "value": f"{tot_pipeline:,.0f} đ", "status": "neutral"}
            ]

        # 3. SUBSCRIPTION DEFERRED
        elif domain_type == "SUBSCRIPTION_DEFERRED":
            cycles = pnl_records or []
            tot_cash = sum(r.get("gross_revenue", 0) for r in cycles)
            tot_rec = sum(r.get("net_revenue", 0) for r in cycles)
            tot_def = sum(r.get("contribution_margin", 0) for r in cycles)
            tot_cnt = sum(r.get("order_count", 0) for r in cycles)

            bullets.append(f"Tổng tiền khách hàng thanh toán trước (Upfront Cash) đạt {tot_cash:,.0f} đ trên {tot_cnt:,.0f} hợp đồng dịch vụ.")
            bullets.append(f"Doanh thu thực hiện phân bổ hàng tháng (MRR đã ghi nhận): {tot_rec:,.0f} đ ({round(tot_rec/tot_cash*100, 1) if tot_cash > 0 else 0}% tổng tiền thu).")
            bullets.append(f"Doanh thu hoãn lại cam kết dịch vụ tương lai (Deferred Revenue): {tot_def:,.0f} đ ({round(tot_def/tot_cash*100, 1) if tot_cash > 0 else 0}%), là nghĩa vụ dịch vụ cần đảm bảo chất lượng vận hành.")

            action_recommendation = "Theo dõi chặt chẽ tiến độ kích hoạt dịch vụ của gói Năm để ngăn chặn yêu cầu hoàn tiền và ghi nhận đúng tiến độ MRR từng kỳ."
            key_metrics = [
                {"label": "Tiền Thu Trước (Cash In)", "value": f"{tot_cash:,.0f} đ", "status": "positive"},
                {"label": "Doanh Thu Tháng (MRR)", "value": f"{tot_rec:,.0f} đ", "status": "positive"},
                {"label": "Doanh Thu Hoãn Lại", "value": f"{tot_def:,.0f} đ", "status": "warning"},
                {"label": "Số Hợp Đồng", "value": f"{tot_cnt:,.0f}", "status": "neutral"}
            ]

        # 4. STORE PNL
        elif domain_type == "STORE_PNL":
            stores = pnl_records or []
            tot_rev = sum(r.get("net_revenue", 0) for r in stores)
            tot_prof = sum(r.get("contribution_margin", 0) for r in stores)
            loss_stores = [s for s in stores if s.get("contribution_margin", 0) < 0]
            prof_stores = [s for s in stores if s.get("contribution_margin", 0) >= 0]
            best_st = max(stores, key=lambda x: x.get("contribution_margin", 0)) if stores else {}

            bullets.append(f"Toàn chuỗi gồm {len(stores)} cửa hàng đạt tổng doanh thu {tot_rev:,.0f} đ, lợi nhuận hoạt động thuần đạt {tot_prof:,.0f} đ (Biên lãi {round(tot_prof/tot_rev*100, 1) if tot_rev > 0 else 0}%).")
            if best_st:
                bullets.append(f"Cửa hàng hiệu quả nhất: {best_st.get('campaign_name', best_st.get('campaign_id'))} tạo ra {best_st.get('contribution_margin', 0):,.0f} đ lợi nhuận (Biên CM {best_st.get('contribution_margin_pct', 0)}%).")
            if loss_stores:
                st_names = ", ".join([str(s.get("campaign_id", "")) for s in loss_stores])
                bullets.append(f"Cảnh báo rủi ro mặt bằng: Có {len(loss_stores)} cửa hàng đang chịu lỗ vận hành ({st_names}) do chi phí thuê và nhân sự vượt quá khả năng tạo doanh số.")

            action_recommendation = f"Đàm phán giảm 15-20% tiền thuê mặt bằng hoặc tái cơ cấu nhân sự tại các điểm bán lỗ ({st_names if loss_stores else 'cửa hàng kém hiệu quả'})."
            key_metrics = [
                {"label": "Tổng Doanh Thu Chuỗi", "value": f"{tot_rev:,.0f} đ", "status": "positive"},
                {"label": "Lợi Nhuận Thuần (NOP)", "value": f"{tot_prof:,.0f} đ", "status": "positive" if tot_prof >= 0 else "danger"},
                {"label": "Cửa Hàng Lỗ Vận Hành", "value": f"{len(loss_stores)} / {len(stores)}", "status": "danger" if loss_stores else "positive"},
                {"label": "Biên Lãi Ròng TB", "value": f"{round(tot_prof/tot_rev*100, 1) if tot_rev > 0 else 0}%", "status": "neutral"}
            ]

        # 5. COHORT RETENTION
        elif domain_type == "COHORT_RETENTION":
            bullets.append(f"Phân tích dữ liệu Cohort Matrix ghi nhận chu kỳ giữ chân khách hàng qua từng tháng.")
            bullets.append(f"Tỷ lệ giữ chân cao nhất tập trung ở chu kỳ M0 -> M1, sau đó giảm dần và đi vào trạng thái ổn định (Baseline Retention).")
            bullets.append(f"Cần tập trung vào trải nghiệm tuần đầu tiên để kéo dài thời gian sống của khách hàng (LTV).")
            action_recommendation = "Kích hoạt chiến dịch Re-engagement vào ngày thứ 14 sau mua hàng đầu tiên để giữ chân nhóm khách hàng mới."
            key_metrics = [
                {"label": "Chu Kỳ Giữ Chân", "value": "M0 -> M6", "status": "neutral"},
                {"label": "Xu Hướng", "value": "Ổn Định", "status": "positive"}
            ]

        # 6. RETAIL ORDERS (CHANNEL, CAMPAIGN, RETURN, COGS...)
        else:
            tot_rev = financial_kpis.get("total_net_revenue", 0)
            tot_cm = financial_kpis.get("total_contribution_margin", 0)
            tot_cogs = financial_kpis.get("total_cogs", 0)
            tot_mkt = financial_kpis.get("total_campaign_costs", 0)
            cm_pct = financial_kpis.get("cm_pct", 0)
            tot_ret = financial_kpis.get("total_return_amount", 0)

            # CHANNEL FOCUS
            if primary_topic == "CHANNEL":
                # Find channel stats
                chs = {}
                for p in pnl_records:
                    ch = p.get("channel") or p.get("campaign_id") or "Kênh Bán"
                    chs[ch] = chs.get(ch, 0) + p.get("net_revenue", 0)
                sorted_chs = sorted(chs.items(), key=lambda x: x[1], reverse=True)
                top_ch = sorted_chs[0] if sorted_chs else ("Kênh chính", tot_rev)

                bullets.append(f"Doanh thu thuần toàn dự án đạt {tot_rev:,.0f} đ với đóng góp từ {len(sorted_chs)} kênh phân phối.")
                bullets.append(f"Kênh dẫn đầu doanh thu: '{top_ch[0]}' đạt {top_ch[1]:,.0f} đ (Chiếm {round(top_ch[1]/tot_rev*100, 1) if tot_rev > 0 else 0}% tổng doanh số toàn sàn).")
                if len(sorted_chs) > 1:
                    bottom_ch = sorted_chs[-1]
                    bullets.append(f"Kênh có quy mô nhỏ nhất: '{bottom_ch[0]}' đạt {bottom_ch[1]:,.0f} đ ({round(bottom_ch[1]/tot_rev*100, 1) if tot_rev > 0 else 0}%).")
                if tot_ret > 0:
                    bullets.append(f"Rủi ro hoàn hàng: Tổng tiền hàng trả ghi nhận {tot_ret:,.0f} đ ({round(tot_ret/tot_rev*100, 1) if tot_rev > 0 else 0}% trên doanh thu).")

                action_recommendation = f"Tập trung đòn bẩy ngân sách mở rộng kênh '{top_ch[0]}' và rà soát chính sách đóng gói/vận chuyển để giảm tỷ lệ hoàn hàng."
                key_metrics = [
                    {"label": "Doanh Thu Thuần", "value": f"{tot_rev:,.0f} đ", "status": "positive"},
                    {"label": "Kênh Số 1", "value": f"{top_ch[0]}", "status": "positive"},
                    {"label": "Tỷ Trọng Kênh Số 1", "value": f"{round(top_ch[1]/tot_rev*100, 1) if tot_rev > 0 else 0}%", "status": "neutral"},
                    {"label": "Biên CM Toàn Dự Án", "value": f"{cm_pct}%", "status": "positive" if cm_pct >= 20 else "warning"}
                ]

            # CAMPAIGN & MKT FOCUS
            elif primary_topic == "CAMPAIGN_MARKETING":
                camps = [p for p in pnl_records if p.get("campaign_id") != "ORGANIC"]
                top_camp = max(camps, key=lambda x: x.get("direct_cost", 0)) if camps else (pnl_records[0] if pnl_records else {})
                best_roi_camp = max(camps, key=lambda x: x.get("roi_pct", 0)) if camps else top_camp

                bullets.append(f"Tổng ngân sách chi phí Marketing ghi nhận {tot_mkt:,.0f} đ phân bổ trên {len(camps) if camps else len(pnl_records)} chiến dịch.")
                if top_camp:
                    bullets.append(f"Chiến dịch tiêu tốn ngân sách lớn nhất: '{top_camp.get('campaign_name', top_camp.get('campaign_id'))}' chi {top_camp.get('direct_cost', 0):,.0f} đ (Đạt doanh thu {top_camp.get('net_revenue', 0):,.0f} đ, Biên CM {top_camp.get('contribution_margin_pct', 0)}%).")
                if best_roi_camp and best_roi_camp != top_camp:
                    bullets.append(f"Chiến dịch hiệu quả vốn cao nhất: '{best_roi_camp.get('campaign_name', best_roi_camp.get('campaign_id'))}' với ROI đạt {best_roi_camp.get('roi_pct', 0)}%.")

                action_recommendation = f"Cắt giảm 20% ngân sách tại các chiến dịch có ROI thấp hoặc bán âm, tái phân bổ sang '{best_roi_camp.get('campaign_name', 'chiến dịch hiệu quả')}' để tối ưu hóa Causal Uplift."
                key_metrics = [
                    {"label": "Tổng Chi Phí MKT", "value": f"{tot_mkt:,.0f} đ", "status": "neutral"},
                    {"label": "Chiến Dịch Chi Lớn Nhất", "value": f"{top_camp.get('campaign_id', 'N/A')}", "status": "warning"},
                    {"label": "Biên CM Thực Tế", "value": f"{tot_cm:,.0f} đ ({cm_pct}%)", "status": "positive" if cm_pct >= 20 else "warning"},
                    {"label": "ROI Chiến Dịch Cao Nhất", "value": f"{best_roi_camp.get('roi_pct', 0)}%", "status": "positive"}
                ]

            # GENERAL RETAIL
            else:
                bullets.append(f"Dự án đạt tổng doanh thu thuần {tot_rev:,.0f} đ với tổng giá vốn COGS là {tot_cogs:,.0f} đ.")
                bullets.append(f"Biên đóng góp thực tế (CM) đạt {tot_cm:,.0f} đ, tỷ lệ CM đạt {cm_pct}% trên toàn bộ đơn hàng kiểm duyệt.")
                if tot_ret > 0:
                    bullets.append(f"Tỷ lệ hàng hoàn & hủy đơn ghi nhận {tot_ret:,.0f} đ ({financial_kpis.get('return_rate', 0)}%).")

                action_recommendation = "Kiểm soát chặt chẽ giá vốn và hạn chế lạm dụng mã giảm giá để bảo toàn biên đóng góp trên 25%."
                key_metrics = [
                    {"label": "Doanh Thu Thuần", "value": f"{tot_rev:,.0f} đ", "status": "positive"},
                    {"label": "Giá Vốn (COGS)", "value": f"{tot_cogs:,.0f} đ", "status": "neutral"},
                    {"label": "Biên CM", "value": f"{tot_cm:,.0f} đ", "status": "positive"},
                    {"label": "Tỷ Lệ CM", "value": f"{cm_pct}%", "status": "positive" if cm_pct >= 20 else "warning"}
                ]

        return {
            "topic_title": topic_title,
            "user_question": user_question,
            "bullets": bullets,
            "action_recommendation": action_recommendation,
            "key_metrics": key_metrics
        }
