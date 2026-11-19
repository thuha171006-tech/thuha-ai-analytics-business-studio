"""
Excel Report Exporter for Sales Campaign Evaluation Agent • Thu Hà Studio
Generates an executive-ready, multi-sheet, beautifully formatted Excel workbook:
- Sheet 1: Tổng Hợp Chỉ Số & Hiệu Quả (thích ứng 100% theo miền dữ liệu: Sản xuất, Cohort, Bán lẻ, SaaS...)
- Sheet 2: Dữ Liệu Đã Làm Sạch (Full Cleaned Dataset)
- Sheet 3: Đề Xuất Chiến Lược & Hành Động (Strategic Action Levers)
- Sheet 4: Báo Cáo Vấn Đề - Giải Pháp (Problem-Solution Matrix)
- Sheet 5: Danh Sách Ngoại Lệ & HITL (Exceptions)
- Sheet 6: Nhật Ký Truy Vết Thực Thi (Audit Trail)
"""

import os
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelReportExporter:
    @staticmethod
    def export(summary: dict, output_path: str = "exports/Bao_Cao_Hieu_Qua_Ban_Hang_ThuHa.xlsx") -> str:
        if os.environ.get("VERCEL") or not os.access(".", os.W_OK):
            import tempfile
            output_path = os.path.join(tempfile.gettempdir(), os.path.basename(output_path))
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        domain = summary.get("domain_type") or "RETAIL_ORDERS"
        is_fin = (summary.get("is_financial") is not False) and (domain not in ["MANUFACTURING_QUALITY", "COHORT_RETENTION", "SALES_FUNNEL"])

        # 1. Prepare DataFrames
        raw_pnl = summary.get("pnl_table", [])
        df_pnl = pd.DataFrame(raw_pnl)

        # Fallback to cleaned_orders_table if attributed_orders_sample is empty
        orders_data = summary.get("cleaned_orders_table") or summary.get("attributed_orders_sample") or []
        df_orders = pd.DataFrame(orders_data)
        
        df_exceptions = pd.DataFrame(summary.get("exceptions_list", []))
        df_audit = pd.DataFrame(summary.get("audit_trail", []))
        matrix = summary.get("problem_solution_matrix", [])
        recs = summary.get("recommendations", [])

        # Column Translation & Order mapping
        col_rename = {
            # Manufacturing columns
            "line_id": "Mã Dây Chuyền",
            "line_name": "Dây Chuyền",
            "lot_count": "Số Lô Sản Xuất",
            "output_qty": "Sản Lượng Đầu Ra (SP)",
            "passed_qty": "Sản Lượng Đạt (SP)",
            "defect_qty": "Số Lỗi Phế Phẩm (SP)",
            "defect_rate_pct": "Tỷ Lệ Lỗi (%)",
            "pass_rate_pct": "Tỷ Lệ Đạt Chuẩn (%)",
            "run_time_minutes": "Thời Gian Vận Hành (Phút)",

            # Cohort columns
            "cohort_name": "Tháng Cohort",
            "new_users": "Khách Hàng Mới",
            "m0_pct": "Tỷ Lệ Giữ Chân M0 (%)",
            "m1_pct": "Tỷ Lệ Giữ Chân M1 (%)",
            "m2_pct": "Tỷ Lệ Giữ Chân M2 (%)",
            "m3_pct": "Tỷ Lệ Giữ Chân M3 (%)",
            "m4_pct": "Tỷ Lệ Giữ Chân M4 (%)",
            "m5_pct": "Tỷ Lệ Giữ Chân M5 (%)",

            # Subscription / SaaS columns
            "cycle": "Chu Kỳ Thu Phí",
            "contracts_count": "Số Hợp Đồng",
            "active_contracts": "Hợp Đồng Hoạt Động",
            "total_upfront": "Tổng Tiền Thu Trước (VND)",
            "recognized_revenue": "Doanh Thu Đã Nhận (VND)",
            "deferred_revenue": "Doanh Thu Hoãn Lại (VND)",

            # Store P&L columns
            "store_id": "Mã Cửa Hàng",
            "store_name": "Tên Cửa Hàng",
            "region": "Khu Vực",
            "revenue": "Doanh Thu (VND)",
            "rental_cost": "Chi Phí Thuê Mặt Bằng (VND)",
            "staff_cost": "Chi Phí Nhân Sự (VND)",
            "operating_cost": "Chi Phí Vận Hành (VND)",
            "net_profit": "Lợi Nhuận Thuần (VND)",
            "profit_margin_pct": "Biên Lợi Nhuận (%)",

            # Sales Funnel columns
            "channel": "Kênh Tiếp Cận",
            "leads_count": "Tổng Số Leads",
            "won_deals": "Deal Thắng (Won)",
            "in_progress_deals": "Deal Đang Đàm Phán",
            "lost_deals": "Deal Thua (Lost)",
            "pipeline_value": "Tổng Giá Trị Phễu (VND)",
            "won_value": "Giá Trị Chốt Thắng (VND)",
            "lost_value": "Giá Trị Thất Thoát (VND)",
            "open_pipeline_value": "Giá Trị Đang Đàm Phán (VND)",
            "win_rate_pct": "Tỷ Lệ Chốt Win Rate (%)",
            "stage": "Giai Đoạn Phễu",
            "conversion_rate_pct": "Tỷ Lệ Chuyển Đổi (%)",
            "deal_value": "Giá Trị Cơ Hội (VND)",

            # Retail P&L columns
            "campaign_id": "Mã Chiến Dịch",
            "campaign_name": "Tên Chiến Dịch / Hạng Mục",
            "orders_count": "Số Đơn Hàng",
            "gross_revenue": "Doanh Thu Gộp (VND)",
            "returns_value": "Hàng Hoàn Trả (VND)",
            "net_revenue": "Doanh Thu Thuần (VND)",
            "cogs": "Giá Vốn COGS (VND)",
            "gross_profit": "Lợi Nhuận Gộp (VND)",
            "discount_cost": "Chiết Khấu Voucher (VND)",
            "direct_cost": "Chi Phí Trực Tiếp (VND)",
            "allocated_overhead": "Chi Phí Phân Bổ (VND)",
            "total_cost": "Tổng Chi Phí (VND)",
            "contribution_margin": "Biên Đóng Góp CM (VND)",
            "contribution_margin_pct": "Biên CM (%)",
            "roi_pct": "ROI (%)",
            "status": "Đánh Giá / Trạng Thái"
        }

        # Filter and rename df_pnl
        if not df_pnl.empty:
            # Drop purely internal technical columns
            drop_internal = ["is_financial"]
            if "line_id" in df_pnl.columns or "line_name" in df_pnl.columns:
                drop_internal.extend(["campaign_id", "campaign_name"])
            if "cohort_name" in df_pnl.columns:
                drop_internal.extend(["campaign_id", "campaign_name"])
            if domain == "SALES_FUNNEL":
                drop_internal.extend(["campaign_id", "net_revenue", "gross_revenue", "cogs", "direct_cost", "overhead_cost", "total_cost", "contribution_margin", "contribution_margin_pct", "roi_pct"])
            cols_to_keep = [c for c in df_pnl.columns if c not in drop_internal]
            df_pnl_clean = df_pnl[cols_to_keep].copy()
            df_pnl_clean.rename(columns=col_rename, inplace=True)
        else:
            df_pnl_clean = pd.DataFrame()

        # Clean df_orders columns (drop technical internals like cleaning_status, attribution_note if present)
        if not df_orders.empty:
            drop_order_tech = ["cleaning_status", "attribution_note"]
            order_cols = [c for c in df_orders.columns if c not in drop_order_tech]
            df_orders_clean = df_orders[order_cols].copy()
        else:
            df_orders_clean = pd.DataFrame()

        # Sheet name based on domain
        sheet1_name = "Tong_Hop_Chi_So"
        if domain == "MANUFACTURING_QUALITY":
            sheet1_name = "Kiem_Soat_Chat_Luong"
        elif domain == "COHORT_RETENTION":
            sheet1_name = "Cohort_Giu_Chan"
        elif domain == "STORE_PNL":
            sheet1_name = "Lai_Lo_Cua_Hang"
        elif domain == "SUBSCRIPTION_DEFERRED":
            sheet1_name = "Doanh_Thu_Dang_Ky"
        elif domain == "SALES_FUNNEL":
            sheet1_name = "Pheu_Ban_Hang"

        # 2. Write to Excel
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if not df_pnl_clean.empty:
                df_pnl_clean.to_excel(writer, sheet_name=sheet1_name, index=False)
            
            if not df_orders_clean.empty:
                df_orders_clean.to_excel(writer, sheet_name="Du_Lieu_Lam_Sach", index=False)
            
            # Sheet: Strategic Recommendations
            if recs:
                df_recs = pd.DataFrame([{
                    "STT": idx + 1,
                    "Mã Hạng Mục": r.get("campaign_id") or f"REC_{idx+1}",
                    "Hạng Mục / Đối Tượng": r.get("campaign_name") or r.get("title", f"Đề xuất {idx+1}"),
                    "Quyết Định Chiến Lược": r.get("decision") or r.get("priority", "TIẾP TỤC TRIỂN KHAI"),
                    "Lý Do Cốt Lõi": r.get("primary_reason") or r.get("desc", ""),
                    "Hành Động Cụ Thể": "; ".join(r.get("action_items") or r.get("actions", [])),
                    "Chỉ Số Đo Lường (Target)": "; ".join(r.get("data_needed") or ([r.get("metric")] if r.get("metric") else []))
                } for idx, r in enumerate(recs)])
                df_recs.to_excel(writer, sheet_name="De_Xuat_Chien_Luoc", index=False)

            # Sheet: Problem-Solution Matrix
            if matrix:
                df_matrix = pd.DataFrame([{
                    "Mã Vấn Đề": m.get("id"),
                    "Mức Độ": m.get("severity"),
                    "Tiêu Đề Vấn Đề": m.get("title"),
                    "Thực Trạng & Bằng Chứng Số Liệu": f"{m.get('problem')} ({m.get('evidence')})",
                    "Nguyên Nhân Cốt Lõi": m.get("root_cause"),
                    "Giải Pháp Khẩn Cấp (24h)": m.get("urgent_solution"),
                    "Giải Pháp Tối Ưu (1-2 Tuần)": m.get("medium_solution"),
                    "Giải Pháp Chiến Lược (A/B)": m.get("strategic_solution"),
                    "Kỳ Vọng Tác Động": m.get("expected_impact")
                } for m in matrix])
                df_matrix.to_excel(writer, sheet_name="Van_De_Giai_Phap", index=False)

            if not df_exceptions.empty:
                df_exceptions.to_excel(writer, sheet_name="Danh_Sach_Ngoai_Le", index=False)
            if not df_audit.empty:
                df_audit.to_excel(writer, sheet_name="Nhat_Ky_Audit_Trail", index=False)

        # 3. Apply Professional Styling with openpyxl
        import openpyxl
        wb = openpyxl.load_workbook(output_path)
        
        header_fill = PatternFill(start_color="183634", end_color="183634", fill_type="solid") # Dark Forest
        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        regular_font = Font(name="Arial", size=10)
        bold_font = Font(name="Arial", size=10, bold=True)
        green_font = Font(name="Arial", size=10, bold=True, color="047857") # Emerald
        red_font = Font(name="Arial", size=10, bold=True, color="B91C1C")   # Red
        
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )

        currency_indicators = ["(vnd)", "doanh thu", "chi phí", "giá vốn", "lợi nhuận", "tiền", "tiền thuê", "lương"]
        percent_indicators = ["(%)", "tỷ lệ", "biên", "roi"]
        quantity_indicators = ["(sp)", "số lô", "số đơn", "khách hàng", "leads", "phút", "sản lượng", "số lỗi"]

        for ws in wb.worksheets:
            # Style header row
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Style data rows
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                for cell in row:
                    cell.font = regular_font
                    cell.border = thin_border
                    col_header = str(ws.cell(1, cell.column).value or "").lower()

                    val = cell.value
                    if isinstance(val, (int, float)):
                        if any(k in col_header for k in currency_indicators):
                            cell.number_format = '#,##0" đ"'
                            cell.alignment = Alignment(horizontal="right")
                        elif any(k in col_header for k in percent_indicators):
                            cell.number_format = '0.00"%"'
                            cell.alignment = Alignment(horizontal="right")
                        elif any(k in col_header for k in quantity_indicators):
                            cell.number_format = '#,##0'
                            cell.alignment = Alignment(horizontal="right")
                        else:
                            cell.number_format = '#,##0'
                            cell.alignment = Alignment(horizontal="right")
                    else:
                        if any(k in col_header for k in ["mã", "stt", "ngày", "trạng thái", "đánh giá", "quyết định"]):
                            cell.alignment = Alignment(horizontal="center")
                        else:
                            cell.alignment = Alignment(horizontal="left")

                    # Highlight alerts
                    if str(cell.value) in ["VƯỢT NGƯỠNG LỖI", "CẦN TÁI CƠ CẤU", "CRITICAL"]:
                        cell.font = red_font
                    elif str(cell.value) in ["ĐẠT CHUẨN CHẤT LƯỢNG", "SINH LỜI TỐT", "TIẾP TỤC TRIỂN KHAI", "SUCCESS"]:
                        cell.font = green_font

            # Auto-adjust column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

        wb.save(output_path)
        return output_path
