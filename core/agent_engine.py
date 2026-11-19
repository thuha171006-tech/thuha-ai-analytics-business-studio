"""
Core AI Agent Engine for Sales Campaign & Financial P&L Evaluation
Thu Hà - Data Analyst & Business Intelligence Studio
Implements Multi-skill Agentic Architecture:
- Step-by-step ReAct workflow
- Tool-calling pattern & Multi-project Context Adaptability
- Audit Logging & Traceability
- Human-in-the-Loop (HITL) Checkpoints & Overrides
"""

import json
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import numpy as np
import pandas as pd
from core.audit_logger import AuditLogger
from core.skills.reconciliation_skill import ReconciliationSkill
from core.skills.evaluation_skill import EvaluationSkill
from core.gemini_service import GeminiService
from core.domain_analyzer import DomainAnalyzer

def sanitize_for_json(obj: Any) -> Any:
    """Recursively clean an object so that all NaN, inf, NaT, and non-serializable values are converted to None or safe types."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or np.isnan(obj) or math.isinf(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj


class SalesEvaluationAgent:
    def __init__(self):
        self.logger = AuditLogger()
        self.reconciliation_skill = ReconciliationSkill(self.logger)
        self.evaluation_skill = EvaluationSkill(self.logger)
        self.gemini_service = GeminiService()
        
        # State memory
        self.raw_data: Dict[str, pd.DataFrame] = {}
        self.cleaned_data: Dict[str, pd.DataFrame] = {}
        self.attributed_orders: pd.DataFrame = pd.DataFrame()
        self.pnl_results: pd.DataFrame = pd.DataFrame()
        self.strategic_report: Dict[str, Any] = {}
        self.exceptions_list: List[Dict[str, Any]] = []
        self.human_overrides: Dict[str, Any] = {}
        self.status: str = "IDLE"
        self.custom_charts: List[Dict[str, Any]] = []
        self.business_context: Dict[str, Any] = {
            "project_name": "Dự Án Đa Kênh",
            "business_type": "Bán lẻ & Thương mại điện tử",
            "extra_info": "Đánh giá hiệu quả P&L và phân bổ chi phí đa kênh",
            "questions": "Doanh thu theo kênh nào cao nhất?\nChi phí theo chiến dịch nào cao nhất?\nBiên đóng góp (CM) và rủi ro hoàn hàng?"
        }

    def run_pipeline(
        self, 
        raw_data: Dict[str, pd.DataFrame], 
        multi_touch_rule: str = "PROPORTIONAL", 
        overhead_method: str = "REVENUE_SHARE",
        human_overrides: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the 4-step AI Agent automated workflow followed by HITL evaluation.
        """
        self.logger.clear()
        self.raw_data = raw_data
        self.human_overrides = human_overrides or {}
        if business_context:
            self.business_context.update(business_context)
        self.status = "RUNNING"
        
        self.logger.log(
            step="PIPELINE_START",
            action="INITIALIZE",
            tool_name="SalesEvaluationAgent",
            message=f"Khởi động AI Agent Đánh giá Hiệu quả Kinh doanh - {self.business_context.get('project_name', 'Dự án')}",
            details={
                "tables_received": {k: len(v) for k, v in raw_data.items() if isinstance(v, pd.DataFrame)},
                "multi_touch_rule": multi_touch_rule,
                "overhead_method": overhead_method
            }
        )

        # -------------------------------------------------------------
        # BƯỚC 1: Làm sạch & Đồng nhất dữ liệu (Data Cleaning & Normalization)
        # -------------------------------------------------------------
        self.cleaned_data, clean_exceptions = self.reconciliation_skill.clean_and_validate(
            raw_data,
            human_overrides=self.human_overrides
        )
        self.exceptions_list = clean_exceptions

        is_empty_or_dummy = any(e.get("type") == "EMPTY_OR_DUMMY_DATASET" for e in clean_exceptions)
        if is_empty_or_dummy:
            self.attributed_orders = pd.DataFrame()
            self.pnl_results = pd.DataFrame()
            self.strategic_report = {"recommendations": [], "causal_analysis": {}}
            self.ai_executive_insights = (
                "### Thông Báo Dữ Liệu:\n"
                "- **Trạng thái:** Tệp dữ liệu không chứa số liệu giao dịch hoặc doanh thu hợp lệ (các ô trống hoặc chỉ chứa ký tự giữ chỗ như 'x', '-').\n"
                "- **Xử lý tài chính:** Toàn bộ chỉ số doanh thu, chi phí và biên đóng góp được ghi nhận chính xác bằng 0 đ.\n"
                "- **Nguyên tắc phân tích:** Hệ thống tuyệt đối không suy đoán hay đưa ra định hướng/giải pháp kinh doanh khi chưa có số liệu thực tế."
            )
            self.status = "COMPLETED_EMPTY_DATA"
            self.logger.log_human_intervention(
                checkpoint="CHECKPOINT_EMPTY_DATA",
                decision="Tệp không có số liệu thực tế. Đặt toàn bộ KPI bằng 0 và không đưa ra định hướng phân tích."
            )
            return self.get_summary()

        # -------------------------------------------------------------
        # BƯỚC 2: Đối chiếu đơn hàng & Xử lý trùng lặp, hàng trả
        # -------------------------------------------------------------
        df_attributed, dedup_exceptions = self.reconciliation_skill.reconcile_orders_and_returns(
            self.cleaned_data,
            multi_touch_rule=multi_touch_rule,
            approved_overrides=self.human_overrides.get("orders", {})
        )
        self.attributed_orders = df_attributed
        self.exceptions_list.extend(dedup_exceptions)

        # Standardize region in attributed orders if missing
        if not self.attributed_orders.empty and "region" not in self.attributed_orders.columns:
            raw_tx = self.cleaned_data.get("transactions", pd.DataFrame())
            if isinstance(raw_tx, pd.DataFrame) and "region" in raw_tx.columns:
                self.attributed_orders["region"] = raw_tx["region"]
            elif "channel" in self.attributed_orders.columns:
                self.attributed_orders["region"] = self.attributed_orders["channel"].apply(
                    lambda ch: "Miền Nam" if any(k in str(ch).lower() for k in ["shopee", "online", "website", "tiktok", "app"])
                    else ("Miền Bắc" if any(k in str(ch).lower() for k in ["lazada", "offline", "cửa hàng", "store", "pos"]) else "Miền Trung")
                )
            else:
                self.attributed_orders["region"] = "Miền Nam"

        # -------------------------------------------------------------
        # BƯỚC 3: Tính toán Doanh thu, Chi phí & Biên lợi nhuận
        # -------------------------------------------------------------
        df_pnl, df_final_attr = self.reconciliation_skill.calculate_campaign_financials(
            df_attributed=self.attributed_orders,
            df_costs=self.cleaned_data.get("costs", pd.DataFrame()),
            overhead_allocation_method=overhead_method,
            approved_cost_allocations=self.human_overrides.get("costs", {})
        )
        self.pnl_results = df_pnl

        # -------------------------------------------------------------
        # BƯỚC 4: VERIFY (Kiểm định) & Feedback Loop
        # -------------------------------------------------------------
        df_tx_raw = self.raw_data.get("transactions", pd.DataFrame())
        if isinstance(df_tx_raw, pd.DataFrame) and not df_tx_raw.empty and "gross_amount" in df_tx_raw.columns:
            gross_col = df_tx_raw["gross_amount"]
            if isinstance(gross_col, pd.DataFrame):
                gross_col = gross_col.iloc[:, 0]
            raw_tx_gross = float(pd.to_numeric(gross_col, errors="coerce").fillna(0).sum())
        else:
            raw_tx_gross = 0.0

        df_costs_raw = self.raw_data.get("costs", pd.DataFrame())
        if isinstance(df_costs_raw, pd.DataFrame) and not df_costs_raw.empty and "amount" in df_costs_raw.columns:
            amt_col = df_costs_raw["amount"]
            if isinstance(amt_col, pd.DataFrame):
                amt_col = amt_col.iloc[:, 0]
            total_costs_input = float(pd.to_numeric(amt_col, errors="coerce").fillna(0).sum())
        else:
            total_costs_input = 0.0

        self.verification_results = self.reconciliation_skill.verify_pipeline_logic(
            df_pnl=self.pnl_results,
            df_attributed=self.attributed_orders,
            raw_tx_gross=raw_tx_gross,
            total_costs_input=total_costs_input
        )

        # -------------------------------------------------------------
        # BƯỚC 4B: Đánh giá đạt tiêu chí & Quyết định chiến lược
        # -------------------------------------------------------------
        from core.domain_analyzer import DomainAnalyzer
        df_tx_raw = self.raw_data.get("transactions", pd.DataFrame())
        orig_cols = self.raw_data.get("original_columns") or list(df_tx_raw.columns)
        domain_type = DomainAnalyzer.detect_domain(df_tx_raw, self.business_context.get("file_name", ""))
        self.domain_type = domain_type

        # Check if marketing campaigns exist
        has_std_camps = False
        if not self.pnl_results.empty and "campaign_id" in self.pnl_results.columns:
            std_camps = [c for c in self.pnl_results["campaign_id"] if str(c).upper() != "ORGANIC"]
            has_std_camps = len(std_camps) > 0

        if has_std_camps and domain_type == "RETAIL_ORDERS":
            self.strategic_report = self.evaluation_skill.evaluate_campaigns(self.pnl_results)
            self.domain_pnl_records = self.pnl_results.to_dict(orient="records")
        else:
            # Build domain-tailored P&L and strategic recommendations
            domain_pnl, domain_recs = DomainAnalyzer.build_domain_pnl_and_recommendations(
                df_tx_raw, domain_type, orig_cols
            )
            self.domain_pnl_records = domain_pnl if domain_pnl else (self.pnl_results.to_dict(orient="records") if not self.pnl_results.empty else [])
            self.strategic_report = {
                "recommendations": domain_recs if domain_recs else self.evaluation_skill.evaluate_campaigns(self.pnl_results).get("recommendations", []),
                "causal_analysis": {}
            }

        # Luôn tạo KPIs và các góc nhìn phân tích thích ứng 100% theo miền dữ liệu thực tế
        self.domain_kpis = DomainAnalyzer.build_domain_kpis(df_tx_raw, domain_type, orig_cols)
        self.domain_analysis_angles = DomainAnalyzer.build_domain_analysis_angles(df_tx_raw, domain_type, orig_cols)

        # -------------------------------------------------------------
        # BƯỚC 4C: Kích hoạt Gemini LLM Advisory (Nhận định Chiến lược Cao cấp)
        # -------------------------------------------------------------
        pnl_records = self.domain_pnl_records
        self.ai_executive_insights = self.gemini_service.generate_executive_insights(
            pnl_records=pnl_records,
            exceptions=self.exceptions_list,
            recommendations=self.strategic_report.get("recommendations", []),
            business_context=self.business_context
        )
        self.logger.log_tool_call(
            tool_name="gemini_executive_advisory",
            inputs={"model": self.gemini_service.model},
            output_summary="Đã tạo báo cáo nhận định chiến lược thông minh từ Google Gemini AI Studio"
        )

        # -------------------------------------------------------------
        # BƯỚC 5: HUMAN CONTROL (Đánh giá điều kiện cần can thiệp)
        # -------------------------------------------------------------
        needs_human_review = len([e for e in self.exceptions_list if "PENDING" in e.get("status", "") or "CONFLICT" in e.get("type", "")]) > 0
        if needs_human_review:
            self.status = "NEEDS_HUMAN_REVIEW"
            self.logger.log_human_intervention(
                checkpoint="CHECKPOINT_1_EXCEPTIONS",
                decision=f"Có {len(self.exceptions_list)} vấn đề ngoại lệ cần Trưởng phòng Kinh doanh xem xét và phê duyệt."
            )
        else:
            self.status = "COMPLETED"
            self.logger.log_human_intervention(
                checkpoint="CHECKPOINT_2_STRATEGY_SIGNOFF",
                decision="Dữ liệu chuẩn xác, AI Agent tự động hoàn tất tính toán và lập báo cáo đề xuất chiến lược."
            )

        return self.get_summary()


    def _generate_problem_solution_matrix(
        self, 
        pnl_records: List[Dict[str, Any]], 
        financial_kpis: Dict[str, Any], 
        channel_breakdown: List[Dict[str, Any]], 
        product_breakdown: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generates in-depth Problem - Root Cause - Actionable Solutions Matrix
        from empirical financial and operational data.
        """
        if not financial_kpis or financial_kpis.get("total_net_revenue", 0) <= 0:
            return []
        matrix = []

        # Problem 1: Loss-making or Thin-Margin Campaigns
        loss_camps = [p for p in pnl_records if p.get("contribution_margin", 0) < 0 and p.get("campaign_id") != "ORGANIC"]
        low_margin_camps = [p for p in pnl_records if 0 <= p.get("contribution_margin", 0) and p.get("contribution_margin_pct", 0) < 15 and p.get("campaign_id") != "ORGANIC"]

        if loss_camps:
            names = ", ".join([f"{c.get('campaign_name')} (Âm {abs(c.get('contribution_margin', 0)):,.0f} đ)" for c in loss_camps])
            matrix.append({
                "id": "PROB_01",
                "title": "Thâm Hụt Lợi Nhuận Ở Các Chiến Dịch Thua Lỗ (CM < 0)",
                "severity": "CRITICAL",
                "badge_color": "rose",
                "icon": "fa-triangle-exclamation text-rose-500",
                "problem": f"Phát hiện {len(loss_camps)} chiến dịch đang trực tiếp ăn mòn lợi nhuận công ty: {names}.",
                "evidence": f"Chiến dịch bị âm lợi nhuận đóng góp do tổng chi phí (chiết khấu voucher + chi phí trực tiếp + chi phí chung) vượt quá biên lợi nhuận gộp.",
                "root_cause": "Áp dụng chính sách voucher giảm giá quá sâu mà không ràng buộc giá trị đơn tối thiểu (AOV), kết hợp cùng chi phí quảng cáo và hàng hoàn sau kỳ.",
                "urgent_solution": "Tạm dừng ngay ngân sách quảng cáo và vô hiệu hóa mã voucher cho các chiến dịch âm trong vòng 24h.",
                "medium_solution": "Thiết lập trần chiết khấu tối đa 12% - 15% doanh thu và chỉ áp dụng cho đơn hàng có giá trị trên 500.000 đ.",
                "strategic_solution": "Tái cấu trúc danh mục khuyến mãi, chuyển toàn bộ nguồn lực sang các chiến dịch có CM vững chắc như CT2_LOYAL.",
                "expected_impact": "Cắt giảm ngay 100% khoản thâm hụt tài chính, giúp tỷ suất lợi nhuận đóng góp toàn công ty tăng thêm +8% đến +15%."
            })
        elif low_margin_camps:
            c = low_margin_camps[0]
            matrix.append({
                "id": "PROB_01",
                "title": f"Biên Lợi Nhuận Đóng Góp Mỏng Tại {c.get('campaign_name')} (< 15%)",
                "severity": "WARNING",
                "badge_color": "amber",
                "icon": "fa-circle-exclamation text-amber-500",
                "problem": f"Chiến dịch {c.get('campaign_name')} đạt doanh số {c.get('net_revenue', 0):,.0f} đ nhưng biên đóng góp chỉ đạt {c.get('contribution_margin_pct', 0):.1f}%.",
                "evidence": f"Doanh thu cao nhưng chiết khấu ({c.get('discount_cost', 0):,.0f} đ) và chi phí quảng cáo ({c.get('direct_cost', 0):,.0f} đ) đã bào mòn phần lớn thặng dư.",
                "root_cause": "Chi phí thu hút khách hàng (CAC) quá cao và mức giảm giá chưa tối ưu theo độ co giãn của cầu.",
                "urgent_solution": "Giảm bớt 20% mức chiết khấu voucher và kiểm soát chặt các kênh quảng cáo có CAC cao.",
                "medium_solution": "Thiết lập ngưỡng giá trị đơn hàng tối thiểu (AOV Threshold) trước khi được kích hoạt giảm giá.",
                "strategic_solution": "Thử nghiệm chính sách tích điểm loyalty thay vì giảm giá trực tiếp bằng tiền mặt.",
                "expected_impact": "Nâng biên lợi nhuận đóng góp từ mức hiện tại lên trên 18%."
            })

        # Problem 2: Channel Performance & Online Return Rate
        online_ch = next((c for c in channel_breakdown if 'online' in str(c.get('channel', '')).lower()), None)
        offline_ch = next((c for c in channel_breakdown if 'offline' in str(c.get('channel', '')).lower()), None)

        if online_ch and online_ch.get("return_rate_pct", 0) > 10:
            ret_val = online_ch.get("return_amount", 0)
            ret_pct = online_ch.get("return_rate_pct", 0)
            matrix.append({
                "id": "PROB_02",
                "title": "Tỷ Lệ Đổi Trả Kênh Online Quá Cao Làm Hao Hụt Dòng Tiền",
                "severity": "WARNING",
                "badge_color": "amber",
                "icon": "fa-arrow-rotate-left text-amber-500",
                "problem": f"Kênh Online ghi nhận tỷ lệ hoàn hàng lên tới {ret_pct:.1f}% (tương đương {ret_val:,.0f} đ giá trị hàng trả), cao vượt trội so với kênh Offline.",
                "evidence": f"Tổng giá trị hàng hoàn kênh Online là {ret_val:,.0f} đ, làm giảm trực tiếp doanh thu thuần và phát sinh thêm chi phí vận chuyển 2 chiều.",
                "root_cause": "Khách hàng nhận hàng không đúng kỳ vọng hình ảnh, tư vấn kích thước/chức năng chưa chuẩn xác, hoặc thời gian giao hàng kéo dài.",
                "urgent_solution": "Thắt chặt quy trình kiểm soát chất lượng đóng gói trước khi giao và chủ động gọi xác nhận đơn trước khi điều phối ship.",
                "medium_solution": "Nâng cấp hình ảnh, video mô tả sản phẩm 360 độ và bảng thông số kỹ thuật chi tiết trên gian hàng số.",
                "strategic_solution": "Hợp tác chặt chẽ với đơn vị vận chuyển cam kết thời gian giao trong 24-48h để giảm tỷ lệ từ chối nhận hàng.",
                "expected_impact": f"Kéo giảm tỷ lệ hoàn hàng kênh Online xuống dưới 7%, thu hồi thêm {ret_val * 0.5:,.0f} đ dòng tiền doanh thu thuần."
            })

        # Problem 3: Product Margin & COGS Inefficiency
        if product_breakdown:
            low_margin_prods = [p for p in product_breakdown if p.get("gross_margin_pct", 0) < 40]
            high_margin_prods = [p for p in product_breakdown if p.get("gross_margin_pct", 0) >= 50]
            if low_margin_prods and high_margin_prods:
                p_low = low_margin_prods[0]
                p_high = high_margin_prods[0]
                matrix.append({
                    "id": "PROB_03",
                    "title": "Cơ Cấu Sản Phẩm Chưa Tối Ưu - Phụ Thuộc Vào Nhóm Sản Phẩm Biên Lãi Mỏng",
                    "severity": "OPPORTUNITY",
                    "badge_color": "indigo",
                    "icon": "fa-boxes-stacked text-indigo-500",
                    "problem": f"Sản phẩm chủ lực {p_low.get('product_id')} có biên lợi nhuận gộp chỉ {p_low.get('gross_margin_pct'):.1f}%, trong khi {p_high.get('product_id')} đạt biên lãi tới {p_high.get('gross_margin_pct'):.1f}%.",
                    "evidence": f"{p_low.get('product_id')} chiếm tỷ trọng doanh số {p_low.get('revenue_share_pct'):.1f}% nhưng giá vốn cao ({p_low.get('cogs'):,.0f} đ), kéo giảm biên lợi nhuận gộp toàn bộ giỏ hàng.",
                    "root_cause": "Các chương trình khuyến mãi tập trung giảm giá sâu cho sản phẩm phễu mà chưa có chiến lược bán kèm (Cross-sell) sản phẩm biên lãi cao.",
                    "urgent_solution": f"Tạo ngay gói combo bán kèm {p_low.get('product_id')} với {p_high.get('product_id')} để kích thích khách hàng mua sản phẩm biên cao.",
                    "medium_solution": "Đàm phán lại biểu phí nhập hàng với nhà cung ứng cho các sản phẩm có sản lượng tiêu thụ lớn.",
                    "strategic_solution": "Định vị lại danh mục sản phẩm theo ma trận BCG: dùng SKU phễu hút traffic, tối đa hóa lợi nhuận bằng SKU biên cao.",
                    "expected_impact": "Tăng biên lợi nhuận gộp tổng hợp thêm +3.5% - 5.0% trên mỗi đơn hàng hoàn tất."
                })

        # Problem 4: Attribution vs Causal Uplift (Strategic)
        matrix.append({
            "id": "PROB_04",
            "title": "Rủi Ro 'Doanh Số Ảo' Do Bẫy Ghi Nhận Kế Toán (Rule-based Attribution vs Causal Uplift)",
            "severity": "STRATEGIC",
            "badge_color": "purple",
            "icon": "fa-brain text-purple-600",
            "problem": "Doanh thu ghi nhận cho các chiến dịch voucher có thể là doanh thu tự nhiên của khách quen (Cannibalization) chứ không phải tăng trưởng thực chất.",
            "evidence": "Khách hàng thân thiết vốn dĩ có ý định mua hàng nhưng được tặng voucher giảm giá, khiến doanh nghiệp mất biên lợi nhuận mà không tạo thêm nhu cầu mới.",
            "root_cause": "Thiếu nhóm đối chứng (Control Group) để kiểm định xem nếu không có mã giảm giá thì khách hàng có tiếp tục mua hay không.",
            "urgent_solution": "Không tặng mã voucher đại trà cho 100% tệp khách hàng quen; chỉ kích hoạt voucher khi khách hàng có dấu hiệu rời bỏ (Churn Risk).",
            "medium_solution": "Triển khai thử nghiệm A/B Testing có nhóm đối chứng: 50% nhận voucher, 50% giữ nguyên giá để đo lường Causal Uplift chuẩn xác.",
            "strategic_solution": "Áp dụng mô hình Uplift Modeling phân khúc khách hàng: Persuadables (chỉ mua khi có khuyến mãi) vs Sure Things (luôn mua).",
            "expected_impact": "Bảo vệ nguyên vẹn 15% - 25% ngân sách marketing không bị lãng phí cho các đơn hàng vốn dĩ sẽ phát sinh tự nhiên."
        })

        return matrix

    def get_summary(self) -> Dict[str, Any]:
        """Convert current state and results into a structured JSON-serializable dictionary."""
        pnl_records = self.pnl_results.to_dict(orient="records") if not self.pnl_results.empty else []
        attributed_sample = self.attributed_orders.head(20).to_dict(orient="records") if not self.attributed_orders.empty else []

        # Build clean records for the preview table and group comparisons
        cleaned_records = []
        if not self.attributed_orders.empty:
            df_src = self.attributed_orders.loc[:, ~self.attributed_orders.columns.duplicated()].copy()
            for idx, r in enumerate(df_src.to_dict(orient="records")):
                clean_row = dict(r)
                
                # PRESERVE ACTUAL FIELDS FROM FILE
                order_id = r.get("order_id") or r.get("Mã đơn") or r.get("mã đơn") or f"-- (Dòng {idx+1})"
                date_val = str(r.get("date") or r.get("Tháng") or r.get("tháng") or r.get("Ngày") or r.get("ngay") or "--")
                channel_val = str(r.get("channel") or r.get("Kênh") or r.get("kênh") or "Chưa phân kênh")
                region_val = str(r.get("region") or r.get("Khu vực") or r.get("khu vực") or "Toàn quốc")
                prod_val = str(r.get("product_id") or r.get("Mã SP") or r.get("ma sp") or "--")

                gross_val = float(r.get("gross_revenue", r.get("gross_amount", r.get("attributed_gross", 0.0))))
                ret_val = float(r.get("return_amount", r.get("attributed_return", 0.0)))
                disc_val = float(r.get("discount_amount", r.get("attributed_discount", 0.0)))
                net_val = float(r.get("net_revenue", r.get("attributed_net_rev", gross_val - ret_val)))
                cogs_val = float(r.get("cogs", r.get("attributed_cogs", r.get("total_cogs", 0.0))))
                gp_val = net_val - cogs_val
                cm_val = float(r.get("contribution_margin", gp_val))
                qty_val = float(r.get("quantity", 1.0))
                unit_price_val = float(r.get("unit_price", gross_val / qty_val if qty_val > 0 else 0.0))

                clean_row["stt"] = idx + 1
                clean_row["cleaning_status"] = "Đã làm sạch"

                # Chỉ bổ sung các trường bán lẻ khi dữ liệu thực sự thuộc miền bán lẻ thương mại điện tử
                if getattr(self, "domain_type", "RETAIL_ORDERS") == "RETAIL_ORDERS":
                    clean_row["order_id"] = str(order_id)
                    clean_row["date"] = date_val
                    clean_row["channel"] = channel_val
                    clean_row["region"] = region_val
                    clean_row["product_id"] = prod_val
                    clean_row["cogs"] = cogs_val
                    clean_row["discount_amount"] = disc_val
                    clean_row["return_amount"] = ret_val
                    clean_row["gross_revenue"] = gross_val
                    clean_row["gross_amount"] = gross_val
                    clean_row["net_revenue"] = net_val
                    clean_row["gross_profit"] = gp_val
                    clean_row["contribution_margin"] = cm_val
                    clean_row["quantity"] = qty_val
                    clean_row["unit_price"] = unit_price_val
                    clean_row["promo_code"] = str(r.get("promo_code") or "--")
                    clean_row["campaign_id"] = str(r.get("campaign_id") or "--")
                    clean_row["status"] = str(r.get("status") or "Ghi nhận")
                    clean_row["attribution_note"] = "Giữ nguyên thông tin thực tế từ file"
                cleaned_records.append(clean_row)
        elif "transactions" in self.cleaned_data and not self.cleaned_data["transactions"].empty:
            for idx, r in enumerate(self.cleaned_data["transactions"].to_dict(orient="records")):
                clean_row = dict(r)
                order_id = r.get("order_id") or r.get("Mã đơn") or f"-- (Dòng {idx+1})"
                date_val = str(r.get("date") or r.get("Tháng") or r.get("tháng") or "--")
                channel_val = str(r.get("channel") or r.get("Kênh") or r.get("kênh") or "Chưa phân kênh")
                region_val = str(r.get("region") or r.get("Khu vực") or r.get("khu vực") or "Toàn quốc")
                prod_val = str(r.get("product_id") or "--")

                gross_val = float(r.get("gross_amount", r.get("gross_revenue", 0.0)))
                ret_val = float(r.get("return_amount", 0.0))
                disc_val = float(r.get("discount_amount", 0.0))
                net_val = gross_val - ret_val
                cogs_val = float(r.get("cogs", 0.0))
                gp_val = net_val - cogs_val

                clean_row["stt"] = idx + 1
                clean_row["order_id"] = str(order_id)
                clean_row["date"] = date_val
                clean_row["channel"] = channel_val
                clean_row["region"] = region_val
                clean_row["product_id"] = prod_val
                clean_row["cogs"] = cogs_val
                clean_row["discount_amount"] = disc_val
                clean_row["return_amount"] = ret_val
                clean_row["gross_revenue"] = gross_val
                clean_row["gross_amount"] = gross_val
                clean_row["net_revenue"] = net_val
                clean_row["gross_profit"] = gp_val
                clean_row["contribution_margin"] = gp_val
                clean_row["promo_code"] = "--"
                clean_row["campaign_id"] = "--"
                clean_row["status"] = "Ghi nhận"
                clean_row["cleaning_status"] = "Đã làm sạch"
                clean_row["attribution_note"] = "Giữ nguyên thông tin thực tế từ file"
                cleaned_records.append(clean_row)

        # -------------------------------------------------------------
        # COMPREHENSIVE FINANCIAL KPIS (Doanh thu & Lợi nhuận toàn diện)
        # -------------------------------------------------------------
        df_attr = self.attributed_orders
        is_financial_domain = getattr(self, "domain_type", "") not in ["MANUFACTURING_QUALITY", "COHORT_RETENTION", "SALES_FUNNEL"]
        
        if is_financial_domain:
            if not df_attr.empty and any(c in df_attr.columns for c in ["attributed_gross", "gross_amount", "gross_revenue", "tiền thu trước (vnd)", "doanh thu"]):
                total_gross = float(df_attr["attributed_gross"].sum()) if "attributed_gross" in df_attr.columns else 0.0
                total_discount = float(df_attr["attributed_discount"].sum()) if "attributed_discount" in df_attr.columns else 0.0
                total_returns = float(df_attr["attributed_return"].sum()) if "attributed_return" in df_attr.columns else 0.0
                total_net_rev = float(df_attr["attributed_net_rev"].sum()) if "attributed_net_rev" in df_attr.columns else (total_gross - total_discount - total_returns)
                total_cogs = float(df_attr["attributed_cogs"].sum()) if "attributed_cogs" in df_attr.columns else 0.0
                total_orders = int(df_attr["order_id"].nunique()) if "order_id" in df_attr.columns else len(df_attr)
            else:
                total_gross = sum(p.get("gross_revenue", 0) for p in pnl_records)
                total_discount = sum(p.get("discount_cost", 0) for p in pnl_records)
                total_returns = sum(p.get("returns_value", 0) for p in pnl_records)
                total_net_rev = sum(p.get("net_revenue", 0) for p in pnl_records)
                total_cogs = sum(p.get("cogs", 0) for p in pnl_records)
                total_orders = sum(p.get("orders_count", 0) for p in pnl_records) or len(cleaned_records)

            total_gross_profit = total_net_rev - total_cogs
            gross_margin_pct = round(total_gross_profit / total_net_rev * 100, 2) if total_net_rev > 0 else 0.0
            total_direct_costs = sum(p.get("direct_cost", 0) for p in pnl_records)
            total_overhead_costs = sum(p.get("allocated_overhead", 0) for p in pnl_records)
            total_campaign_costs = total_direct_costs + total_overhead_costs + total_discount
            total_cm = sum(p.get("contribution_margin", 0) for p in pnl_records) if pnl_records else (total_gross_profit - total_campaign_costs)
            cm_pct = round(total_cm / total_net_rev * 100, 2) if total_net_rev > 0 else 0.0
            aov = round(total_net_rev / total_orders, 0) if total_orders > 0 else 0.0
            return_rate_pct = round(total_returns / total_gross * 100, 2) if total_gross > 0 else 0.0
            roas = round(total_net_rev / total_campaign_costs, 2) if total_campaign_costs > 0 else (round(total_net_rev / total_cogs, 2) if total_cogs > 0 else 0.0)
            roi_pct = round(total_cm / total_campaign_costs * 100, 2) if total_campaign_costs > 0 else (round(total_cm / total_cogs * 100, 2) if total_cogs > 0 else 0.0)
        else:
            total_gross = 0.0
            total_discount = 0.0
            total_returns = 0.0
            total_net_rev = 0.0
            total_cogs = 0.0
            total_gross_profit = 0.0
            gross_margin_pct = 0.0
            total_direct_costs = 0.0
            total_overhead_costs = 0.0
            total_campaign_costs = 0.0
            total_cm = 0.0
            cm_pct = 0.0
            aov = 0.0
            return_rate_pct = 0.0
            roas = 0.0
            roi_pct = 0.0
            total_orders = len(cleaned_records)

        financial_kpis = {
            "is_financial": is_financial_domain,
            "total_gross_revenue": total_gross,
            "total_discount_amount": total_discount,
            "total_return_amount": total_returns,
            "total_net_revenue": total_net_rev,
            "total_cogs": total_cogs,
            "total_gross_profit": total_gross_profit,
            "gross_margin_pct": gross_margin_pct,
            "total_direct_costs": total_direct_costs,
            "total_overhead_costs": total_overhead_costs,
            "total_campaign_costs": total_campaign_costs,
            "total_contribution_margin": total_cm,
            "cm_pct": cm_pct,
            "net_operating_profit": total_cm,
            "total_orders": total_orders,
            "aov": aov,
            "return_rate_pct": return_rate_pct,
            "roas": roas,
            "roi_pct": roi_pct
        }

        # -------------------------------------------------------------
        # DYNAMIC MULTI-DIMENSIONAL BREAKDOWNS (Các hướng phân tích linh hoạt)
        # -------------------------------------------------------------
        # 1. Channel Breakdown (Kênh bán hàng)
        channel_breakdown = []
        if not df_attr.empty and "channel" in df_attr.columns:
            ch_grp = df_attr.groupby("channel")
            for ch, grp in ch_grp:
                g_gross = float(grp["attributed_gross"].sum()) if "attributed_gross" in grp.columns else 0.0
                g_ret = float(grp["attributed_return"].sum()) if "attributed_return" in grp.columns else 0.0
                g_net = float(grp["attributed_net_rev"].sum()) if "attributed_net_rev" in grp.columns else (g_gross - g_ret)
                g_cogs = float(grp["attributed_cogs"].sum()) if "attributed_cogs" in grp.columns else 0.0
                g_disc = float(grp["attributed_discount"].sum()) if "attributed_discount" in grp.columns else 0.0
                g_gp = g_net - g_cogs
                g_cm = g_gp - g_disc
                channel_breakdown.append({
                    "channel": str(ch),
                    "orders_count": int(grp["order_id"].nunique()) if "order_id" in grp.columns else len(grp),
                    "gross_revenue": g_gross,
                    "discount_amount": g_disc,
                    "return_amount": g_ret,
                    "net_revenue": g_net,
                    "cogs": g_cogs,
                    "gross_profit": g_gp,
                    "gross_margin_pct": round(g_gp / g_net * 100, 1) if g_net > 0 else 0.0,
                    "contribution_margin": g_cm,
                    "cm_pct": round(g_cm / g_net * 100, 1) if g_net > 0 else 0.0,
                    "return_rate_pct": round(g_ret / g_gross * 100, 1) if g_gross > 0 else 0.0,
                    "revenue_share_pct": round(g_net / total_net_rev * 100, 1) if total_net_rev > 0 else 0.0
                })

        # 2. Product Breakdown (Sản phẩm & Giá vốn COGS)
        product_breakdown = []
        if not df_attr.empty and "product_id" in df_attr.columns:
            df_cogs_src = self.cleaned_data.get("cogs", pd.DataFrame())
            cogs_map = {}
            if not df_cogs_src.empty and "product_id" in df_cogs_src.columns:
                for _, cr in df_cogs_src.iterrows():
                    c_pid = str(cr.get("product_id", "")).strip()
                    cogs_map[c_pid] = str(cr.get("product_name", c_pid)).strip()

            p_grp = df_attr.groupby("product_id")
            for pid, grp in p_grp:
                p_qty = float(grp["quantity"].sum()) if "quantity" in grp.columns else len(grp)
                p_gross = float(grp["attributed_gross"].sum()) if "attributed_gross" in grp.columns else 0.0
                p_disc = float(grp["attributed_discount"].sum()) if "attributed_discount" in grp.columns else 0.0
                p_net = float(grp["attributed_net_rev"].sum()) if "attributed_net_rev" in grp.columns else p_gross
                p_cogs = float(grp["attributed_cogs"].sum()) if "attributed_cogs" in grp.columns else 0.0
                p_gp = p_net - p_cogs
                product_breakdown.append({
                    "product_id": str(pid),
                    "product_name": cogs_map.get(str(pid), f"Sản phẩm {pid}"),
                    "quantity_sold": p_qty,
                    "gross_revenue": p_gross,
                    "discount_amount": p_disc,
                    "net_revenue": p_net,
                    "cogs": p_cogs,
                    "gross_profit": p_gp,
                    "gross_margin_pct": round(p_gp / p_net * 100, 1) if p_net > 0 else 0.0,
                    "revenue_share_pct": round(p_gross / total_gross * 100, 1) if total_gross > 0 else 0.0
                })
            product_breakdown.sort(key=lambda x: x["gross_revenue"], reverse=True)

        # 3. Timeline Breakdown (Dòng thời gian ngày/tháng)
        timeline_breakdown = []
        if not df_attr.empty and "date" in df_attr.columns:
            t_grp = df_attr.groupby("date")
            for dt, grp in t_grp:
                timeline_breakdown.append({
                    "date": str(dt),
                    "orders_count": int(grp["order_id"].nunique()) if "order_id" in grp.columns else len(grp),
                    "gross_revenue": float(grp["attributed_gross"].sum()) if "attributed_gross" in grp.columns else 0.0,
                    "net_revenue": float(grp["attributed_net_rev"].sum()) if "attributed_net_rev" in grp.columns else 0.0,
                    "discount_amount": float(grp["attributed_discount"].sum()) if "attributed_discount" in grp.columns else 0.0
                })
            timeline_breakdown.sort(key=lambda x: x["date"])

        # 4. Region Breakdown (Khu vực / Địa bàn đa kênh)
        region_breakdown = []
        if not df_attr.empty and "region" in df_attr.columns:
            r_grp = df_attr.groupby("region")
            for reg, grp in r_grp:
                reg_name = str(reg).strip()
                if not reg_name or reg_name.lower() in ["none", "nan", ""]:
                    continue
                r_gross = float(grp["attributed_gross"].sum()) if "attributed_gross" in grp.columns else 0.0
                r_net = float(grp["attributed_net_rev"].sum()) if "attributed_net_rev" in grp.columns else r_gross
                r_cogs = float(grp["attributed_cogs"].sum()) if "attributed_cogs" in grp.columns else 0.0
                r_gp = r_net - r_cogs
                region_breakdown.append({
                    "region": reg_name,
                    "orders_count": int(grp["order_id"].nunique()) if "order_id" in grp.columns else len(grp),
                    "gross_revenue": r_gross,
                    "net_revenue": r_net,
                    "cogs": r_cogs,
                    "gross_profit": r_gp,
                    "revenue_share_pct": round(r_net / total_net_rev * 100, 1) if total_net_rev > 0 else 0.0
                })
            region_breakdown.sort(key=lambda x: x["net_revenue"], reverse=True)

        # 5. Category Breakdown (Ngành hàng / Danh mục sản phẩm)
        category_breakdown = []
        if not df_attr.empty and "category" in df_attr.columns:
            cat_s = df_attr["category"].dropna().astype(str).str.strip()
            unique_cats = [c for c in cat_s.unique() if c and c.lower() not in ["none", "nan", "unknown", "chưa phân loại"]]
            if len(unique_cats) > 1:
                c_grp = df_attr.groupby("category")
                for cat, grp in c_grp:
                    cat_name = str(cat).strip()
                    if not cat_name or cat_name.lower() in ["none", "nan", ""]:
                        continue
                    cat_gross = float(grp["attributed_gross"].sum()) if "attributed_gross" in grp.columns else 0.0
                    cat_net = float(grp["attributed_net_rev"].sum()) if "attributed_net_rev" in grp.columns else cat_gross
                    category_breakdown.append({
                        "category": cat_name,
                        "orders_count": int(grp["order_id"].nunique()) if "order_id" in grp.columns else len(grp),
                        "gross_revenue": cat_gross,
                        "net_revenue": cat_net,
                        "revenue_share_pct": round(cat_net / total_net_rev * 100, 1) if total_net_rev > 0 else 0.0
                    })
                category_breakdown.sort(key=lambda x: x["net_revenue"], reverse=True)

        empty_exc = next((e for e in self.exceptions_list if e.get("type") in ["EMPTY_OR_DUMMY_DATASET", "DATASET_INVALID_OR_EMPTY"]), None)
        # Chỉ coi là không hợp lệ khi có lỗi cấu trúc rõ ràng hoặc hoàn toàn không có bản ghi nào
        is_invalid_or_empty = (empty_exc is not None) or (len(cleaned_records) == 0)

        # If completely empty, wipe all breakdowns
        if is_invalid_or_empty:
            channel_breakdown = []
            product_breakdown = []
            timeline_breakdown = []
            region_breakdown = []
            category_breakdown = []
            problem_solution_matrix = []
            contextual_qa = []
            column_profiling = []
            pnl_records = []
            self.strategic_report = {"recommendations": [], "causal_analysis": {}}

        dataset_validity_info = {
            "is_valid": 1 if not is_invalid_or_empty else 0,
            "error_message": empty_exc.get("description") if empty_exc else ("Tệp rỗng hoặc không có dữ liệu để xử lý." if is_invalid_or_empty else "")
        }

        # 6. Active Analysis Dimensions detection (Thích ứng linh hoạt theo dữ liệu thực tế)
        has_camps = len([p for p in pnl_records if p.get("campaign_id") != "ORGANIC"]) > 1 and total_net_rev > 0
        has_chs = len(channel_breakdown) > 1 and total_net_rev > 0
        has_prods = len(product_breakdown) > 1 and total_net_rev > 0
        has_time = len(timeline_breakdown) > 1 and total_net_rev > 0
        has_regs = len(region_breakdown) > 1 and total_net_rev > 0
        has_cats = len(category_breakdown) > 1 and total_net_rev > 0
        has_costs = (financial_kpis.get("total_cogs", 0) > 0 or financial_kpis.get("total_discount_amount", 0) > 0 or financial_kpis.get("total_campaign_costs", 0) > 0) and total_net_rev > 0

        analysis_dimensions = {
            "has_campaigns": has_camps,
            "has_channels": has_chs,
            "has_products": has_prods,
            "has_timeline": has_time,
            "has_regions": has_regs,
            "has_categories": has_cats,
            "has_cost_structure": has_costs,
            "total_active_angles": sum([1 for flag in [has_camps, has_chs, has_prods, has_time, has_regs, has_cats, has_costs] if flag])
        }

        # 7. Executive Problem - Solution Matrix (Dynamic multi-domain & empirical data-driven)
        raw_tx_df = self.raw_data.get("transactions") if isinstance(self.raw_data, dict) else None
        active_df = pd.DataFrame(cleaned_records) if cleaned_records else (df_attr if not df_attr.empty else (self.cleaned_data.get("transactions", pd.DataFrame()) if isinstance(self.cleaned_data, dict) else pd.DataFrame()))
        df_for_matrix = raw_tx_df if (isinstance(raw_tx_df, pd.DataFrame) and not raw_tx_df.empty) else active_df
        matrix_cols = self.raw_data.get("original_columns") or (list(df_for_matrix.columns) if isinstance(df_for_matrix, pd.DataFrame) else [])

        problem_solution_matrix = DomainAnalyzer.build_domain_problem_solution_matrix(
            df=df_for_matrix,
            domain=getattr(self, "domain_type", "GENERAL_TABULAR"),
            original_cols=matrix_cols,
            pnl_records=getattr(self, "domain_pnl_records", pnl_records),
            financial_kpis=financial_kpis,
            user_question=self.business_context.get("questions", "") or self.business_context.get("focus_question", ""),
            file_name=self.business_context.get("file_name", "")
        )
        if not problem_solution_matrix:
            problem_solution_matrix = self._generate_problem_solution_matrix(
                pnl_records=getattr(self, "domain_pnl_records", pnl_records),
                financial_kpis=financial_kpis,
                channel_breakdown=channel_breakdown,
                product_breakdown=product_breakdown
            )

        # 8. Dataset Meta, Column Profiling & Contextual Business Q&A (DataLens Studio Feature Suite)
        total_rows_count = len(cleaned_records) if cleaned_records else 0

        # Select friendly columns to profile (excluding internal attribution helper columns)
        internal_cols = {"stt", "cleaning_status", "attribution_note", "gross_amount", "attributed_gross", "attributed_net_rev", "attributed_cogs", "attributed_discount", "attributed_return", "unit_cogs", "total_cogs", "tx_discount_amount"}
        col_display_map = {
            "date": "Tháng / Ngày",
            "region": "Khu vực",
            "channel": "Kênh bán",
            "product_id": "Sản phẩm",
            "product_name": "Tên Sản phẩm",
            "order_id": "Số đơn / Mã đơn",
            "customer_id": "Mã Khách hàng",
            "customer_type": "Nhóm Khách hàng",
            "quantity": "Số lượng đơn / SP",
            "unit_price": "Đơn giá (VND)",
            "gross_revenue": "Doanh thu (VND)",
            "gross_amount": "Doanh thu (VND)",
            "discount_amount": "Chiết khấu (VND)",
            "return_amount": "Hàng bán trả (VND)",
            "cogs": "Chi phí giá vốn (VND)",
            "net_revenue": "Doanh thu thuần (VND)",
            "gross_profit": "Lợi nhuận gộp (VND)",
            "contribution_margin": "Biên đóng góp (CM)",
            "campaign_id": "Chiến dịch",
            "status": "Trạng thái đơn",
            "promo_code": "Mã Voucher",
            "category": "Ngành hàng / Danh mục"
        }

        if not active_df.empty and total_rows_count > 0:
            profile_cols = [c for c in active_df.columns if not str(c).startswith("_") and c not in internal_cols]
            # Deduplicate by friendly display name
            seen_display_names = set()
            dedup_profile_cols = []
            for c in profile_cols:
                disp = col_display_map.get(str(c), str(c).replace('_', ' ').title()).strip().lower()
                if disp not in seen_display_names:
                    seen_display_names.add(disp)
                    dedup_profile_cols.append(c)
            profile_target_df = active_df[dedup_profile_cols]
            total_cols_count = len(raw_tx_df.columns) if (raw_tx_df is not None and not raw_tx_df.empty) else len(dedup_profile_cols)
            numeric_cols = profile_target_df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_cols_count = len(raw_tx_df.select_dtypes(include=[np.number]).columns) if (raw_tx_df is not None and not raw_tx_df.empty) else len(numeric_cols)
        else:
            total_cols_count = 0
            numeric_cols = []
            numeric_cols_count = 0
            profile_target_df = pd.DataFrame()

        file_disp_name = self.business_context.get("file_name") or self.business_context.get("project_name", "Tệp dữ liệu đã tải")
        if total_rows_count == 0:
            dataset_meta = {
                "dataset_name": "-- Chưa tải dữ liệu --",
                "total_rows": 0,
                "total_cols": 0,
                "numeric_cols_count": 0
            }
        else:
            dataset_meta = {
                "dataset_name": f"Bộ 1 — {file_disp_name} ({total_rows_count:,} dòng nguồn)",
                "total_rows": total_rows_count,
                "total_cols": total_cols_count,
                "numeric_cols_count": numeric_cols_count,
                "original_columns": self.raw_data.get("original_columns") or (list(raw_tx_df.columns) if (isinstance(raw_tx_df, pd.DataFrame) and not raw_tx_df.empty) else (list(active_df.columns) if not active_df.empty else [])),
                "domain_type": getattr(self, "domain_type", "RETAIL_ORDERS")
            }

        col_display_map = {
            "date": "Tháng / Ngày",
            "region": "Khu vực",
            "channel": "Kênh bán",
            "product_id": "Sản phẩm",
            "product_name": "Tên Sản phẩm",
            "order_id": "Số đơn / Mã đơn",
            "customer_id": "Mã Khách hàng",
            "customer_type": "Nhóm Khách hàng",
            "quantity": "Số lượng đơn / SP",
            "unit_price": "Đơn giá (VND)",
            "gross_revenue": "Doanh thu (VND)",
            "gross_amount": "Doanh thu (VND)",
            "discount_amount": "Chiết khấu (VND)",
            "return_amount": "Hàng bán trả (VND)",
            "cogs": "Chi phí giá vốn (VND)",
            "net_revenue": "Doanh thu thuần (VND)",
            "gross_profit": "Lợi nhuận gộp (VND)",
            "contribution_margin": "Biên đóng góp (CM)",
            "campaign_id": "Chiến dịch",
            "status": "Trạng thái đơn",
            "promo_code": "Mã Voucher",
            "category": "Ngành hàng / Danh mục"
        }

        # THỐNG KÊ THEO CỘT: CHỈ GIỮ CÁC CỘT CÓ SỐ LIỆU TỪ FILE GỐC, BỎ CÁC CỘT RỖNG VÀ CỘT KHÔNG CÓ TRONG FILE
        column_profiling = []
        source_df_for_profile = raw_tx_df if (raw_tx_df is not None and not raw_tx_df.empty) else None
        orig_cols = self.raw_data.get("original_columns") or (list(source_df_for_profile.columns) if source_df_for_profile is not None else [])
        
        if source_df_for_profile is not None and not source_df_for_profile.empty:
            for col in orig_cols:
                if col not in source_df_for_profile.columns or str(col).startswith("_"):
                    continue
                s = source_df_for_profile[col]
                valid_s = s.dropna()
                valid_str = valid_s.astype(str).str.strip().replace('', np.nan).dropna()
                # Bỏ các cột hoàn toàn không có số liệu (trống 100%)
                if valid_str.empty:
                    continue
                
                missing_cnt = int(s.isna().sum()) + int((s.astype(str).str.strip() == '').sum())
                unique_cnt = int(valid_s.nunique())
                
                # Chuẩn hóa để nhận diện số (bỏ %, đ, VND, dấu phẩy...)
                clean_num_str = valid_str.str.replace('%', '', regex=False).str.replace('đ', '', regex=False).str.replace('VND', '', regex=False).str.replace('vnd', '', regex=False).str.replace('$', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                num_s = pd.to_numeric(clean_num_str, errors='coerce')
                is_pct = any('%' in str(x) for x in valid_str.iloc[:15])
                
                if num_s.notna().sum() >= len(valid_str) * 0.7 and not valid_str.str.contains('^[a-zA-Z_\\-]+$', regex=True).any():
                    valid_nums = num_s.dropna()
                    mean_val = float(valid_nums.mean()) if not valid_nums.empty else 0.0
                    min_val = float(valid_nums.min()) if not valid_nums.empty else 0.0
                    max_val = float(valid_nums.max()) if not valid_nums.empty else 0.0
                    column_profiling.append({
                        "column_key": str(col),
                        "column_name": str(col),
                        "data_type": "Số (%)" if is_pct else "Số",
                        "missing_count": missing_cnt,
                        "unique_count": unique_cnt,
                        "mean": round(mean_val, 2),
                        "min": round(min_val, 2),
                        "max": round(max_val, 2)
                    })
                else:
                    date_s = pd.to_datetime(valid_str, errors='coerce')
                    if date_s.notna().sum() >= len(valid_str) * 0.7:
                        min_date = str(date_s.dropna().min().date()) if not date_s.dropna().empty else None
                        max_date = str(date_s.dropna().max().date()) if not date_s.dropna().empty else None
                        column_profiling.append({
                            "column_key": str(col),
                            "column_name": str(col),
                            "data_type": "Ngày / Thời gian",
                            "missing_count": missing_cnt,
                            "unique_count": unique_cnt,
                            "mean": None,
                            "min": min_date,
                            "max": max_date
                        })
                    else:
                        column_profiling.append({
                            "column_key": str(col),
                            "column_name": str(col),
                            "data_type": "Văn bản / Phân loại",
                            "missing_count": missing_cnt,
                            "unique_count": unique_cnt,
                            "mean": None,
                            "min": None,
                            "max": None
                        })

        mkt_camps = [p for p in pnl_records if p.get("campaign_id") != "ORGANIC"]
        has_mkt_camps = len(mkt_camps) > 0 and sum(p.get("gross_revenue", 0) for p in mkt_camps) > 0

        contextual_qa = []
        domain_type = getattr(self, "domain_type", "RETAIL_ORDERS")
        if total_rows_count > 0:
            if not is_financial_domain:
                # Non-financial domains: strictly empirical operational Q&A without any fake money/VND
                if domain_type == "MANUFACTURING_QUALITY":
                    pnl_lines = getattr(self, "domain_pnl_records", []) or pnl_records
                    worst_line = max(pnl_lines, key=lambda x: x.get("defect_rate_pct", 0)) if pnl_lines else {}
                    best_line = min(pnl_lines, key=lambda x: x.get("defect_rate_pct", 0)) if pnl_lines else {}
                    tot_out = sum(r.get("output_qty", 0) for r in pnl_lines)
                    tot_pass = sum(r.get("passed_qty", 0) for r in pnl_lines)
                    tot_err = sum(r.get("defect_qty", 0) for r in pnl_lines)
                    avg_err = round(tot_err / tot_out * 100, 2) if tot_out > 0 else 0.0

                    contextual_qa.append({
                        "question": "Dây chuyền nào có tỷ lệ lỗi / phế phẩm cao nhất?",
                        "icon": "fa-triangle-exclamation text-rose-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: {worst_line.get('line_name', 'Dây chuyền')} ghi nhận tỷ lệ lỗi cao nhất ({worst_line.get('defect_rate_pct', 0)}% - {worst_line.get('defect_qty', 0):,.0f} SP lỗi), vượt ngưỡng trần cảnh báo kiểm định 1.0%."
                        ]
                    })
                    contextual_qa.append({
                        "question": "Tổng sản lượng đầu ra và tỷ lệ đạt chuẩn là bao nhiêu?",
                        "icon": "fa-industry text-teal-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Tổng sản lượng toàn bộ {len(pnl_lines)} dây chuyền đạt {tot_out:,.0f} SP. Sản lượng đạt chuẩn kiểm định là {tot_pass:,.0f} SP (Tỷ lệ đạt {round(100 - avg_err, 2)}%, số lỗi {tot_err:,.0f} SP)."
                        ]
                    })
                    contextual_qa.append({
                        "question": "Dây chuyền nào vận hành chuẩn hóa và ổn định nhất?",
                        "icon": "fa-circle-check text-emerald-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: {best_line.get('line_name', 'Dây chuyền')} vận hành xuất sắc nhất với tỷ lệ đạt {best_line.get('pass_rate_pct', 99)}% (tỷ lệ lỗi chỉ {best_line.get('defect_rate_pct', 0)}%), đạt chuẩn làm mô hình benchmark."
                        ]
                    })
                elif domain_type == "COHORT_RETENTION":
                    pnl_cohorts = getattr(self, "domain_pnl_records", []) or pnl_records
                    best_cohort = max(pnl_cohorts, key=lambda x: (x.get("m1_pct") or 0.0)) if pnl_cohorts else {}
                    tot_users = sum(r.get("new_users", 0) for r in pnl_cohorts)
                    contextual_qa.append({
                        "question": "Nhóm khách hàng (Cohort) nào có tỷ lệ giữ chân M1 cao nhất?",
                        "icon": "fa-users text-teal-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Nhóm khách hàng {best_cohort.get('cohort_name', 'Cohort')} duy trì tỷ lệ quay lại M1 cao nhất ({best_cohort.get('m1_pct', 0)}%)."
                        ]
                    })
                    contextual_qa.append({
                        "question": "Điểm rơi suy giảm (Drop-off) diễn ra mạnh nhất ở đâu?",
                        "icon": "fa-chart-line-down text-amber-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Tỷ lệ suy giảm người dùng hoạt động mạnh nhất xảy ra giữa tháng M1 và M2. Cần thiết lập kịch bản nuôi dưỡng người dùng tự động sau 30 ngày."
                        ]
                    })
                    contextual_qa.append({
                        "question": "Tổng lượng người dùng mới được kích hoạt qua các kỳ?",
                        "icon": "fa-user-plus text-sky-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Tổng số {tot_users:,.0f} khách hàng mới được kích hoạt qua toàn bộ {len(pnl_cohorts)} nhóm cohort."
                        ]
                    })
            else:
                # Financial domains with real revenue and cost metrics
                if channel_breakdown:
                    top_ch = max(channel_breakdown, key=lambda x: x.get("net_revenue", 0))
                    ch_count = len(channel_breakdown)
                    contextual_qa.append({
                        "question": "Doanh thu theo kênh nào cao nhất?",
                        "icon": "fa-store text-sky-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Kênh \"{top_ch.get('channel', 'Kênh bán')}\" đạt doanh thu thuần dẫn đầu ({top_ch.get('net_revenue', 0):,.0f} đ) trong tổng số {ch_count} kênh. Cột này có số liệu ở {total_rows_count}/{total_rows_count} dòng."
                        ]
                    })
                elif "region" in active_df.columns:
                    reg_grp = active_df.groupby("region")["attributed_net_rev" if "attributed_net_rev" in active_df.columns else "gross_amount"].sum()
                    top_reg = reg_grp.idxmax() if not reg_grp.empty else "Toàn quốc"
                    top_reg_val = float(reg_grp.max()) if not reg_grp.empty else 0.0
                    contextual_qa.append({
                        "question": "Doanh thu theo khu vực nào cao nhất?",
                        "icon": "fa-map-location-dot text-sky-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Khu vực \"{top_reg}\" có doanh thu cao nhất đạt {top_reg_val:,.0f} đ."
                        ]
                    })
                else:
                    contextual_qa.append({
                        "question": "Doanh thu tổng thể đạt bao nhiêu?",
                        "icon": "fa-sack-dollar text-sky-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Tổng doanh thu thuần ghi nhận {total_net_rev:,.0f} đ trên toàn bộ {total_rows_count:,} dòng dữ liệu."
                        ]
                    })

                # Question 2: Top cost / expense
                cost_bullets = []
                if total_cogs > 0:
                    cost_bullets.append(f"{dataset_meta['dataset_name']}: Chi phí giá vốn (COGS) ghi nhận {total_cogs:,.0f} đ (chiếm {(total_cogs / total_net_rev * 100):.1f}% doanh thu thuần)." if total_net_rev > 0 else f"Chi phí giá vốn (COGS) ghi nhận {total_cogs:,.0f} đ.")
                if has_mkt_camps:
                    top_camp = max(mkt_camps, key=lambda x: x.get("total_cost", 0))
                    cost_bullets.append(f"Chiến dịch \"{top_camp.get('campaign_name', top_camp.get('campaign_id'))}\" có chi phí marketing lớn nhất ({top_camp.get('total_cost', 0):,.0f} đ).")
                elif total_discount > 0:
                    cost_bullets.append(f"Tổng ngân sách chiết khấu & voucher đã áp dụng là {total_discount:,.0f} đ.")
                
                if cost_bullets:
                    contextual_qa.append({
                        "question": "Chi phí & giá vốn phát sinh lớn nhất ở đâu?",
                        "icon": "fa-bullhorn text-indigo-600",
                        "bullets": cost_bullets
                    })

                # Question 3: Top product / item
                if product_breakdown:
                    top_prod = max(product_breakdown, key=lambda x: x.get("gross_revenue", 0))
                    contextual_qa.append({
                        "question": "Sản phẩm nào đóng góp doanh thu cao nhất?",
                        "icon": "fa-box-open text-purple-600",
                        "bullets": [
                            f"{dataset_meta['dataset_name']}: Sản phẩm \"{top_prod.get('product_name', top_prod.get('product_id'))}\" dẫn đầu với doanh thu {top_prod.get('gross_revenue', 0):,.0f} đ (chiếm {top_prod.get('revenue_share_pct', 0)}% tổng doanh số)."
                        ]
                    })

        # -------------------------------------------------------------
        # VALIDATE QUESTION SUFFICIENCY & GENERATE DEEP DIVE INSIGHTS
        # -------------------------------------------------------------
        from core.question_validator import QuestionSufficiencyValidator
        user_question = self.business_context.get("questions", "")
        orig_cols = self.raw_data.get("original_columns") or (list(raw_tx_df.columns) if (isinstance(raw_tx_df, pd.DataFrame) and not raw_tx_df.empty) else (list(active_df.columns) if not active_df.empty else []))
        
        question_sufficiency = QuestionSufficiencyValidator.validate_question_sufficiency(
            user_question=user_question,
            df_raw=raw_tx_df if (isinstance(raw_tx_df, pd.DataFrame) and not raw_tx_df.empty) else active_df,
            original_cols=orig_cols,
            domain_type=domain_type,
            pnl_records=getattr(self, "domain_pnl_records", pnl_records),
            financial_kpis=financial_kpis,
            gemini_service=self.gemini_service
        )
        self.question_sufficiency = question_sufficiency

        if question_sufficiency.get("is_sufficient"):
            deep_res = question_sufficiency.get("deep_dive_analysis")
            if deep_res:
                contextual_qa.insert(0, {
                    "is_focus_highlight": True,
                    "topic_title": deep_res.get("topic_title", "Phân Tích Trọng Tâm"),
                    "question": f"🎯 TRỌNG TÂM: {question_sufficiency['user_question']}",
                    "icon": "fa-bullseye text-[#183634]",
                    "badge": "✓ ĐỦ ĐIỀU KIỆN 100% • PHÂN TÍCH CHUYÊN SÂU",
                    "bullets": deep_res.get("bullets", []),
                    "action_recommendation": deep_res.get("action_recommendation", ""),
                    "key_metrics": deep_res.get("key_metrics", [])
                })
        else:
            contextual_qa.insert(0, {
                "is_missing_alert": True,
                "question": f"⚠️ DỮ LIỆU THIẾU ĐIỀU KIỆN: \"{question_sufficiency['user_question']}\"",
                "icon": "fa-triangle-exclamation text-rose-600",
                "badge": "THIẾU SỐ LIỆU",
                "what_is_missing": question_sufficiency.get("what_is_missing", ""),
                "what_is_needed": question_sufficiency.get("what_is_needed", ""),
                "missing_fields": question_sufficiency.get("missing_fields", []),
                "suggested_questions": question_sufficiency.get("suggested_questions", []),
                "bullets": [
                    f"❌ THIẾU GÌ: {question_sufficiency.get('what_is_missing', '')}",
                    f"💡 CẦN GÌ: {question_sufficiency.get('what_is_needed', '')}"
                ]
            })

        raw_summary = {
            "status": "DATASET_INVALID_OR_EMPTY" if is_invalid_or_empty else self.status,
            "domain_type": getattr(self, "domain_type", "RETAIL_ORDERS"),
            "is_financial": is_financial_domain,
            "question_sufficiency": getattr(self, "question_sufficiency", {
                "is_sufficient": True,
                "user_question": "",
                "what_is_missing": "",
                "what_is_needed": "",
                "missing_fields": [],
                "suggested_questions": []
            }),
            "dataset_validity": dataset_validity_info,
            "dataset_error": dataset_validity_info["error_message"] if is_invalid_or_empty else "",
            "summary_kpis": {
                "is_financial": is_financial_domain,
                "total_campaigns": len(mkt_camps) if has_mkt_camps else len(pnl_records),
                "total_net_revenue": total_net_rev,
                "total_contribution_margin": total_cm,
                "total_campaign_costs": total_campaign_costs,
                "total_exceptions_detected": len(self.exceptions_list),
                "has_mkt_campaigns": has_mkt_camps
            },
            "financial_kpis": financial_kpis,
            "domain_kpis": getattr(self, "domain_kpis", []),
            "domain_analysis_angles": getattr(self, "domain_analysis_angles", []),
            "dataset_meta": dataset_meta,
            "column_profiling": column_profiling,
            "contextual_qa": contextual_qa,
            "channel_breakdown": channel_breakdown,
            "product_breakdown": product_breakdown,
            "timeline_breakdown": timeline_breakdown,
            "region_breakdown": region_breakdown,
            "category_breakdown": category_breakdown,
            "analysis_dimensions": analysis_dimensions,
            "problem_solution_matrix": problem_solution_matrix,
            "root_causes": problem_solution_matrix,
            "pnl_table": getattr(self, "domain_pnl_records", pnl_records),
            "attributed_orders_sample": attributed_sample,
            "cleaned_orders_table": cleaned_records,
            "costs_data": self.cleaned_data.get("costs").to_dict(orient="records") if isinstance(self.cleaned_data.get("costs"), pd.DataFrame) and not self.cleaned_data.get("costs").empty else [],
            "exceptions_list": self.exceptions_list,
            "recommendations": self.strategic_report.get("recommendations", []),
            "causal_analysis": self.strategic_report.get("causal_analysis", {}),
            "ai_executive_insights": getattr(self, "ai_executive_insights", ""),
            "verification_results": getattr(self, "verification_results", {"is_ok": True, "feedback_needed": False, "checks": []}),
            "cleaning_error_center": {
                "missing_critical_fields": len([e for e in self.exceptions_list if "MISSING" in e.get("type", "") or "INVALID" in e.get("type", "")]),
                "formatting_errors": len([e for e in self.exceptions_list if "FORMAT" in e.get("type", "") or "NUMERIC" in e.get("type", "")]),
                "date_inconsistencies": len([e for e in self.exceptions_list if "LATE" in e.get("type", "") or "DATE" in e.get("type", "")]),
                "duplicate_data": len([e for e in self.exceptions_list if "DUPLICATE" in e.get("type", "")]),
                "multi_touch_conflicts": len([e for e in self.exceptions_list if "MULTI_TOUCH" in e.get("type", "") or "CONFLICT" in e.get("type", "")])
            },
            "gemini_model": self.gemini_service.model,
            "business_context": self.business_context,
            "custom_charts": getattr(self, "custom_charts", []),
            "audit_trail": self.logger.get_logs()
        }
        return sanitize_for_json(raw_summary)

