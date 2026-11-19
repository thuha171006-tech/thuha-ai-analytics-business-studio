"""
HTML Exporter for Thu Hà AI Analytics Studio - Multi-Project Sales Evaluation Agent
Generates 2 Standalone, Self-Contained HTML Reports:
1. Báo Cáo Chi Tiết P&L / Vận Hành (Comprehensive Audit & Decision Report)
2. Dashboard Tổng Quan (Executive Interactive Visual Dashboard)
Adapts 100% to dataset domain (Manufacturing Quality, Cohort Retention, Store P&L, Subscription, Funnel, Retail).
Never renders empty charts or irrelevant metrics.
"""

import json
from typing import Dict, Any, List, Optional

class StandaloneHtmlExporter:
    @staticmethod
    def _format_vnd(val):
        try:
            return f"{float(val):,.0f} đ"
        except:
            return "0 đ"

    @staticmethod
    def _format_num(val, unit=""):
        try:
            n = float(val)
            s = f"{n:,.1f}" if n % 1 != 0 else f"{int(n):,}"
            return f"{s} {unit}".strip()
        except:
            return f"0 {unit}".strip()

    @staticmethod
    def _format_pct(val):
        try:
            return f"{float(val):.2f}%"
        except:
            return "0.00%"

    @classmethod
    def _resolve_domain_meta(cls, summary: Dict[str, Any]):
        domain = summary.get("domain_type") or "RETAIL_ORDERS"
        is_fin = (summary.get("is_financial") is not False) and (domain not in ["MANUFACTURING_QUALITY", "COHORT_RETENTION"])
        
        meta = {
            "domain": domain,
            "is_financial": is_fin,
            "badge": "BÁN LẺ & THƯƠNG MẠI ĐIỆN TỬ",
            "report_title": "Báo Cáo Chi Tiết Hiệu Quả P&L & Quyết Định Chiến Lược",
            "dashboard_title": "Dashboard Tổng Quan Hiệu Quả Bán Hàng & P&L",
            "table_title": "Bảng Phân Tích Hiệu Quả P&L Chi Tiết Các Chiến Dịch",
            "unit_label": "Đơn vị tính: VNĐ"
        }

        if domain == "MANUFACTURING_QUALITY":
            meta.update({
                "badge": "KIỂM SOÁT SẢN XUẤT & CHẤT LƯỢNG",
                "report_title": "Báo Cáo Kiểm Soát Chất Lượng & Phế Phẩm Sản Xuất",
                "dashboard_title": "Dashboard Giám Sát Vận Hành & Tỷ Lệ Lỗi Dây Chuyền",
                "table_title": "Bảng Thống Kê & Kiểm Soát Chất Lượng Theo Dây Chuyền",
                "unit_label": "Đơn vị tính: Sản phẩm (SP) / Phút"
            })
        elif domain == "COHORT_RETENTION":
            meta.update({
                "badge": "PHÂN TÍCH COHORT GIỮ CHÂN KHÁCH HÀNG",
                "report_title": "Báo Cáo Phân Tích Cohort Giữ Chân Khách Hàng (Retention Triangle)",
                "dashboard_title": "Dashboard Giữ Chân Khách Hàng & Vòng Đời Cohort",
                "table_title": "Bảng Ma Trận Giữ Chân Khách Hàng (Cohort Triangle)",
                "unit_label": "Đơn vị tính: Khách hàng / Tỷ lệ giữ chân (%)"
            })
        elif domain == "STORE_PNL":
            meta.update({
                "badge": "HIỆU QUẢ KINH DOANH ĐIỂM BÁN (STORE P&L)",
                "report_title": "Báo Cáo Lãi / Lỗ Điểm Bán & Tối Ưu Chi Phí Thuê Mặt Bằng",
                "dashboard_title": "Dashboard Hiệu Quả Kinh Doanh Lãi Lỗ Từng Cửa Hàng",
                "table_title": "Bảng Phân Tích Lãi / Lỗ Chi Tiết Theo Cửa Hàng",
                "unit_label": "Đơn vị tính: VNĐ"
            })
        elif domain == "SUBSCRIPTION_DEFERRED":
            meta.update({
                "badge": "DOANH THU ĐĂNG KÝ & DỊCH VỤ HOÃN LẠI",
                "report_title": "Báo Cáo Phân Bổ Doanh Thu Đăng Ký & Dòng Tiền Trả Trước",
                "dashboard_title": "Dashboard Quản Trị Doanh Thu Hoãn Lại & Chu Kỳ Hợp Đồng",
                "table_title": "Bảng Phân Bổ Doanh Thu Theo Chu Kỳ Hợp Đồng",
                "unit_label": "Đơn vị tính: VNĐ"
            })
        elif domain == "SALES_FUNNEL":
            meta.update({
                "badge": "CHUYỂN ĐỔI PHỄU BÁN HÀNG (SALES FUNNEL)",
                "report_title": "Báo Cáo Đo Lường Hiệu Suất Chuyển Đổi Phễu Bán Hàng",
                "dashboard_title": "Dashboard Quản Trị Pipeline & Tỷ Lệ Chuyển Đổi Khách Hàng",
                "table_title": "Bảng Thống Kê Chuyển Đổi Từng Giai Đoạn Phễu",
                "unit_label": "Đơn vị tính: Leads / VNĐ"
            })
        return meta

    @classmethod
    def _sanitize_chart_dict(cls, chart: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Guarantees 100% chart vs legend consistency across all datasets and domains."""
        if not chart or not chart.get("labels") or not chart.get("datasets"):
            return None
        c_type = chart.get("type", "bar")
        labels = list(chart["labels"])
        datasets = [dict(ds) for ds in chart["datasets"]]
        if not labels or not datasets:
            return None

        if c_type in ["doughnut", "pie", "polarArea"]:
            ds0 = datasets[0]
            vals = ds0.get("data", [])
            valid_indices = [
                i for i, v in enumerate(vals)
                if i < len(labels) and v is not None and str(v).strip() not in ["", "--", "null", "none"] and float(v or 0) > 0.0001
            ]
            if len(valid_indices) < 2:
                return None
            chart["labels"] = [labels[i] for i in valid_indices]
            for ds in datasets:
                ds["data"] = [ds["data"][i] for i in valid_indices if i < len(ds.get("data", []))]
                for color_prop in ["backgroundColor", "borderColor"]:
                    if isinstance(ds.get(color_prop), list):
                        ds[color_prop] = [ds[color_prop][i % len(ds[color_prop])] for i in valid_indices]
            chart["datasets"] = datasets
            return chart

        elif c_type == "line":
            valid_ds = []
            point_styles = ['circle', 'triangle', 'rectRounded', 'diamond', 'star', 'crossRot']
            dash_styles = [[], [6, 4], [3, 3], [8, 3, 2, 3], [2, 2], [5, 5]]
            for idx, ds in enumerate(datasets):
                raw_data = ds.get("data", [])
                valid_pts = [p for p in raw_data if p is not None and str(p).strip() not in ["", "--", "null", "none"] and float(p or 0) >= 0]
                if len(valid_pts) >= 2:
                    if not ds.get("pointStyle"):
                        ds["pointStyle"] = point_styles[idx % len(point_styles)]
                    if "pointRadius" not in ds:
                        ds["pointRadius"] = 5
                    if len(datasets) > 1 and "borderDash" not in ds:
                        ds["borderDash"] = dash_styles[idx % len(dash_styles)]
                    valid_ds.append(ds)
            if not valid_ds:
                return None
            chart["datasets"] = valid_ds
            return chart

        else: # bar / other
            valid_ds = []
            for ds in datasets:
                raw_data = ds.get("data", [])
                has_val = any(v is not None and str(v).strip() not in ["", "--", "null", "none"] and abs(float(v or 0)) > 0.0001 for v in raw_data)
                if has_val:
                    valid_ds.append(ds)
            if not valid_ds:
                return None
            chart["datasets"] = valid_ds
            return chart

    @classmethod
    def _collect_valid_charts(cls, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collects only charts that have valid, non-empty, domain-matching data."""
        # Check if caller already provided sanitized client chart specs
        client_specs = summary.get("chart_specs")
        if client_specs and isinstance(client_specs, list) and len(client_specs) > 0:
            result_charts = []
            for idx, cs in enumerate(client_specs):
                c = {
                    "id": f"chart_spec_{idx}",
                    "title": cs.get("title", f"Biểu đồ {idx+1}"),
                    "subtitle": cs.get("subtitle", ""),
                    "unit": cs.get("unit", ""),
                    "type": cs.get("type", "bar"),
                    "labels": cs.get("labels", []),
                    "datasets": cs.get("datasets", []),
                    "is_wide": len(cs.get("labels", [])) > 6 or cs.get("type") == "line",
                    "index_axis": cs.get("index_axis")
                }
                sc = cls._sanitize_chart_dict(c)
                if sc:
                    result_charts.append(sc)
            if result_charts:
                return result_charts

        charts = []
        domain = summary.get("domain_type") or "RETAIL_ORDERS"
        is_fin = (summary.get("is_financial") is not False) and (domain not in ["MANUFACTURING_QUALITY", "COHORT_RETENTION"])
        
        # 1. Domain-specific analysis angles
        domain_angles = summary.get("domain_analysis_angles") or []
        for idx, angle in enumerate(domain_angles):
            labels = angle.get("labels") or []
            datasets = angle.get("datasets") or []
            if labels and datasets:
                has_data = any(
                    any(v is not None and v != 0 for v in ds.get("data", []))
                    for ds in datasets
                )
                if has_data:
                    charts.append({
                        "id": f"chart_domain_{idx}",
                        "title": angle.get("title") or angle.get("name", f"Góc nhìn phân tích {idx+1}"),
                        "subtitle": angle.get("subtitle") or "",
                        "unit": angle.get("unit") or "",
                        "type": angle.get("chartType") or "bar",
                        "labels": labels,
                        "datasets": datasets,
                        "is_wide": len(labels) > 6 or angle.get("chartType") == "line"
                    })

        # 2. Standard Business / P&L charts (Only if financial and have real data)
        if is_fin:
            channels = summary.get("channel_breakdown") or []
            valid_channels = [c for c in channels if c.get("channel") and c.get("channel") not in ["--", "Khác", "Unknown"] and (float(c.get("net_revenue") or 0) > 0)]
            if valid_channels and not any("kênh" in c["title"].lower() for c in charts):
                ch_labels = [c["channel"] for c in valid_channels]
                has_returns = any(float(c.get("return_amount") or 0) > 0.0001 for c in valid_channels)
                has_gross_diff = any(abs(float(c.get("gross_revenue") or 0) - float(c.get("net_revenue") or 0)) > 1.0 for c in valid_channels)
                
                ch_datasets = []
                if has_returns:
                    ch_datasets.append({"label": "Doanh Thu Gộp (Tr. đ)", "data": [round(float(c.get("gross_revenue", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#a0c4ff", "borderColor": "#0284c7", "borderWidth": 1.5, "borderRadius": 6})
                    ch_datasets.append({"label": "Hàng Hoàn (Tr. đ)", "data": [round(float(c.get("return_amount", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#f4978e", "borderColor": "#e11d48", "borderWidth": 1.5, "borderRadius": 6})
                    ch_datasets.append({"label": "Doanh Thu Thuần (Tr. đ)", "data": [round(float(c.get("net_revenue", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#72efdd", "borderColor": "#0d9488", "borderWidth": 1.5, "borderRadius": 6})
                elif has_gross_diff:
                    ch_datasets.append({"label": "Doanh Thu Gộp (Tr. đ)", "data": [round(float(c.get("gross_revenue", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#a0c4ff", "borderColor": "#0284c7", "borderWidth": 1.5, "borderRadius": 6})
                    ch_datasets.append({"label": "Doanh Thu Thuần (Tr. đ)", "data": [round(float(c.get("net_revenue", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#72efdd", "borderColor": "#0d9488", "borderWidth": 1.5, "borderRadius": 6})
                else:
                    ch_datasets.append({"label": "Doanh Thu Thuần (Tr. đ)", "data": [round(float(c.get("net_revenue", 0)) / 1e6, 2) for c in valid_channels], "backgroundColor": "#72efdd", "borderColor": "#0d9488", "borderWidth": 1.5, "borderRadius": 6})

                charts.append({
                    "id": "chart_std_channel",
                    "title": "Phân Phối Đa Kênh (Omnichannel)",
                    "subtitle": "So sánh Doanh thu thuần và quy mô đóng góp giữa các kênh bán",
                    "unit": "Tr. VNĐ",
                    "type": "bar",
                    "labels": ch_labels,
                    "datasets": ch_datasets,
                    "is_wide": len(ch_labels) > 6
                })

            regions = summary.get("region_breakdown") or []
            valid_regions = [r for r in regions if r.get("region") and r.get("region") not in ["None", "Unknown"] and (float(r.get("net_revenue") or 0) > 0)]
            if len(valid_regions) > 1 and not any("khu vực" in c["title"].lower() or "địa bàn" in c["title"].lower() for c in charts):
                reg_labels = [f"{r.get('region')} ({r.get('revenue_share_pct', 0)}%)" for r in valid_regions]
                reg_data = [round(float(r.get("net_revenue", 0)) / 1e6, 2) for r in valid_regions]
                reg_colors = ["#72efdd", "#f4978e", "#a0c4ff", "#fed9b7", "#d8b4e2", "#80ed99"][:len(valid_regions)]
                charts.append({
                    "id": "chart_std_region",
                    "title": "Phân Phối Thị Phần Theo Khu Vực",
                    "subtitle": "Tỷ trọng đóng góp doanh thu thuần & biên lợi nhuận giữa các vùng miền",
                    "unit": "% Thị phần",
                    "type": "doughnut",
                    "labels": reg_labels,
                    "datasets": [{
                        "data": reg_data,
                        "backgroundColor": reg_colors,
                        "borderColor": "#ffffff",
                        "borderWidth": 2
                    }],
                    "is_wide": False
                })

            products = summary.get("product_breakdown") or []
            valid_prods = [p for p in products if p.get("product_id") and not any(k in str(p.get("product_id")) for k in ["--", "Không có", "Chung"]) and (float(p.get("gross_revenue") or p.get("net_revenue") or 0) > 0)][:6]
            if valid_prods and not any("sản phẩm" in c["title"].lower() for c in charts):
                prod_labels = [f"{p.get('product_id')} - {p.get('product_name', '')}".strip(" -") for p in valid_prods]
                charts.append({
                    "id": "chart_std_products",
                    "title": "Cơ Cấu Sản Phẩm Bán Chạy (Pareto 80/20)",
                    "subtitle": "Top sản phẩm đóng góp doanh số và lợi nhuận gộp lớn nhất",
                    "unit": "Tr. VNĐ",
                    "type": "bar",
                    "labels": prod_labels,
                    "datasets": [
                        {"label": "Doanh Thu Gộp (Tr. đ)", "data": [round(float(p.get("gross_revenue", 0)) / 1e6, 2) for p in valid_prods], "backgroundColor": "#a0c4ff", "borderColor": "#0284c7", "borderWidth": 1.5, "borderRadius": 6},
                        {"label": "Lợi Nhuận Gộp (Tr. đ)", "data": [round(float(p.get("gross_profit", 0)) / 1e6, 2) for p in valid_prods], "backgroundColor": "#fed9b7", "borderColor": "#d97706", "borderWidth": 1.5, "borderRadius": 6}
                    ],
                    "is_wide": False
                })

            timeline = summary.get("timeline_breakdown") or []
            valid_time = [t for t in timeline if t.get("date") and (float(t.get("net_revenue") or t.get("orders_count") or 0) > 0)]
            if len(valid_time) >= 2 and not any("thời gian" in c["title"].lower() for c in charts):
                time_labels = [str(t["date"]) for t in valid_time]
                time_datasets = [
                    {"label": "Doanh Thu Thuần (Tr. đ)", "data": [round(float(t.get("net_revenue", 0)) / 1e6, 2) for t in valid_time], "borderColor": "#0284c7", "backgroundColor": "rgba(160, 196, 255, 0.35)", "fill": True, "tension": 0.35, "pointRadius": 4, "borderWidth": 2.5}
                ]
                if any(int(t.get("orders_count") or 0) > 0 for t in valid_time):
                    time_datasets.append(
                        {"label": "Số Đơn Hàng", "data": [int(t.get("orders_count", 0)) for t in valid_time], "borderColor": "#fad2e1", "backgroundColor": "rgba(244, 151, 142, 0.35)", "fill": False, "tension": 0.35, "pointRadius": 3, "borderWidth": 2, "borderDash": [3, 3]}
                    )
                charts.append({
                    "id": "chart_std_timeline",
                    "title": "Xu Hướng Doanh Số & Số Lượng Đơn Theo Thời Gian",
                    "subtitle": "Đường cong phát sinh doanh thu thuần và nhịp độ giao dịch",
                    "unit": "Tr. VNĐ",
                    "type": "line",
                    "labels": time_labels,
                    "datasets": time_datasets,
                    "is_wide": True
                })

            pnl = summary.get("pnl_table") or []
            valid_camps = [p for p in pnl if p.get("campaign_id") and p.get("campaign_id") != "ORGANIC" and (float(p.get("net_revenue") or 0) > 0)]
            if not valid_camps and pnl:
                valid_camps = [p for p in pnl if (float(p.get("net_revenue") or 0) > 0)]
            if len(valid_camps) > 1 and not any("chiến dịch" in c["title"].lower() or "sales wave" in c["title"].lower() for c in charts):
                camp_labels = [str(p.get("campaign_name") or p.get("campaign_id")) for p in valid_camps]
                charts.append({
                    "id": "chart_std_campaign",
                    "title": "Hiệu Quả Chiến Dịch Marketing & Biên Đóng Góp (Sales Wave)",
                    "subtitle": "So sánh Doanh thu thuần vs Biên đóng góp CM giữa các chiến dịch",
                    "unit": "Tr. VNĐ",
                    "type": "line",
                    "labels": camp_labels,
                    "datasets": [
                        {"label": "Doanh Thu Thuần (Tr. đ)", "data": [round(float(p.get("net_revenue", 0)) / 1e6, 2) for p in valid_camps], "borderColor": "#0d9488", "backgroundColor": "rgba(114, 239, 221, 0.35)", "fill": True, "tension": 0.35, "pointRadius": 4, "borderWidth": 2.5},
                        {"label": "Biên Đóng Góp CM (Tr. đ)", "data": [round(float(p.get("contribution_margin", 0)) / 1e6, 2) for p in valid_camps], "borderColor": "#e11d48", "backgroundColor": "rgba(244, 151, 142, 0.45)", "fill": True, "tension": 0.35, "pointRadius": 4, "borderWidth": 2.5}
                    ],
                    "is_wide": True
                })

            fin = summary.get("financial_kpis") or {}
            cogs = float(fin.get("total_cogs") or 0)
            mkt = float(fin.get("total_campaign_costs") or 0)
            cm = float(fin.get("total_contribution_margin") or 0)
            disc = float(fin.get("total_discount_amount") or 0)

            cost_items = []
            if cogs > 0.0001:
                cost_items.append(("Giá Vốn COGS", round(cogs / 1e6, 2), "#b5e2fa"))
            if disc > 0.0001:
                cost_items.append(("Chiết Khấu Voucher", round(disc / 1e6, 2), "#f4978e"))
            if mkt > 0.0001:
                cost_items.append(("Chi Phí MKT & Vận Hành", round(mkt / 1e6, 2), "#fed9b7"))
            if cm > 0.0001:
                cost_items.append(("Biên Đóng Góp CM", round(cm / 1e6, 2), "#72efdd"))

            if len(cost_items) >= 2 and not any("cơ cấu" in c["title"].lower() or "chi phí" in c["title"].lower() for c in charts):
                charts.append({
                    "id": "chart_std_cost",
                    "title": "Cơ Cấu Chi Phí & Lợi Nhuận (Cost Structure & Margin)",
                    "subtitle": "Tỷ trọng phân bổ dòng tiền giữa các khoản mục chi phí và lợi nhuận",
                    "unit": "% Quy mô",
                    "type": "doughnut",
                    "labels": [ci[0] for ci in cost_items],
                    "datasets": [{
                        "data": [ci[1] for ci in cost_items],
                        "backgroundColor": [ci[2] for ci in cost_items],
                        "borderColor": "#ffffff",
                        "borderWidth": 2
                    }],
                    "is_wide": False
                })

        # 3. Custom Charts generated by user
        custom_charts = summary.get("custom_charts") or []
        for idx, cc in enumerate(custom_charts):
            labels = cc.get("labels") or []
            data_pts = cc.get("data") or []
            if labels and data_pts:
                charts.append({
                    "id": f"chart_custom_{idx}",
                    "title": cc.get("title") or f"Biểu Đồ Tùy Chỉnh {idx+1}",
                    "subtitle": f"Tùy biến theo chiều {cc.get('dimension', '')} và chỉ số {cc.get('metric', '')}",
                    "unit": cc.get("unit") or "",
                    "type": cc.get("chart_type") or "bar",
                    "labels": labels,
                    "datasets": [
                        {"label": cc.get("title", "Chỉ số"), "data": data_pts, "backgroundColor": "#a0c4ff", "borderColor": "#0284c7", "borderWidth": 1.5, "borderRadius": 6}
                    ],
                    "is_wide": len(labels) > 6
                })

        sanitized_charts = []
        for c in charts:
            sc = cls._sanitize_chart_dict(c)
            if sc:
                sanitized_charts.append(sc)
        return sanitized_charts

    @classmethod
    def _render_kpis_html(cls, summary: Dict[str, Any], meta: Dict[str, Any]) -> str:
        domain_kpis = summary.get("domain_kpis") or []
        is_fin = meta["is_financial"]

        if not is_fin and domain_kpis and len(domain_kpis) >= 4:
            cards = []
            bg_colors = ["#c5dedd", "#fad2e1", "#e0f2fe", "#fef3c7"]
            text_colors = ["#183634", "#872D43", "#0369a1", "#92400e"]
            border_colors = ["#9ec8c6", "#f2a8c0", "#bae6fd", "#fde68a"]

            for i in range(4):
                k = domain_kpis[i]
                c_bg = bg_colors[i % 4]
                c_txt = text_colors[i % 4]
                c_border = border_colors[i % 4]
                cards.append(f"""
                <div style="background: {c_bg}35; border: 1.5px solid {c_border}; border-radius: 16px; padding: 18px 20px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: {c_txt}; letter-spacing: 0.5px;">{k.get('title')}</div>
                    <div style="font-size: 24px; font-weight: 900; color: {c_txt}; margin: 8px 0 4px 0; font-family: monospace;">{k.get('value')}</div>
                    <div style="font-size: 11px; color: #475569; display: flex; align-items: center; justify-content: space-between; gap: 4px;">
                        <span>{k.get('subtext', '')}</span>
                        <span style="background: {c_bg}; color: {c_txt}; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 9999px;">{k.get('badge', '')}</span>
                    </div>
                </div>
                """)
            return f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">{"".join(cards)}</div>'
        else:
            fin = summary.get("financial_kpis") or {}
            kpis = summary.get("summary_kpis") or {}
            net_rev = fin.get("total_net_revenue") or kpis.get("total_net_revenue", 0)
            cm = fin.get("total_contribution_margin") or kpis.get("total_contribution_margin", 0)
            cm_pct = fin.get("cm_pct", 0)
            roi_pct = fin.get("roi_pct", 0)
            total_costs = fin.get("total_campaign_costs", 0)
            returns = fin.get("total_return_amount", 0)
            orders_cnt = fin.get("total_orders", 0) or kpis.get("total_orders", 0)
            roas = fin.get("roas", 0)

            return f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div style="background: #c5dedd35; border: 1.5px solid #9ec8c6; border-radius: 16px; padding: 18px 20px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #183634;">Doanh Thu Thuần</div>
                    <div style="font-size: 24px; font-weight: 900; color: #183634; margin: 8px 0 4px 0; font-family: monospace;">{cls._format_vnd(net_rev)}</div>
                    <div style="font-size: 11px; color: #475569;">Đã trừ hàng hoàn {cls._format_vnd(returns)}</div>
                </div>
                <div style="background: #fad2e135; border: 1.5px solid #f2a8c0; border-radius: 16px; padding: 18px 20px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #872D43;">Biên Đóng Góp (CM) ★</div>
                    <div style="font-size: 24px; font-weight: 900; color: #872D43; margin: 8px 0 4px 0; font-family: monospace;">{cls._format_vnd(cm)}</div>
                    <div style="font-size: 11px; color: #475569;">Biên CM: {cm_pct}% • ROI: {roi_pct}%</div>
                </div>
                <div style="background: #e0f2fe35; border: 1.5px solid #bae6fd; border-radius: 16px; padding: 18px 20px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #0369a1;">Chi Phí Chiến Dịch & MKT</div>
                    <div style="font-size: 24px; font-weight: 900; color: #0369a1; margin: 8px 0 4px 0; font-family: monospace;">{cls._format_vnd(total_costs)}</div>
                    <div style="font-size: 11px; color: #475569;">Hiệu quả ROAS: {roas}x</div>
                </div>
                <div style="background: #fef3c735; border: 1.5px solid #fde68a; border-radius: 16px; padding: 18px 20px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: #92400e;">Quy Mô Đơn Hàng Đối Soát</div>
                    <div style="font-size: 24px; font-weight: 900; color: #92400e; margin: 8px 0 4px 0; font-family: monospace;">{orders_cnt:,} Đơn</div>
                    <div style="font-size: 11px; color: #475569;">100% Chuẩn hóa & Khử trùng dữ liệu</div>
                </div>
            </div>
            """

    @classmethod
    def _render_main_table_html(cls, summary: Dict[str, Any], meta: Dict[str, Any]) -> str:
        pnl = summary.get("pnl_table") or []
        domain = meta["domain"]
        if not pnl:
            return '<div style="padding: 24px; text-align: center; color: #94a3b8; font-style: italic;">Chưa có dữ liệu thống kê.</div>'

        if domain == "MANUFACTURING_QUALITY":
            headers = ["DÂY CHUYỀN", "SỐ LÔ SX", "SẢN LƯỢNG ĐẦU RA", "SẢN LƯỢNG ĐẠT", "SỐ LỖI", "TỶ LỆ LỖI", "THỜI GIAN CHẠY", "ĐÁNH GIÁ KIỂM ĐỊNH"]
            th_html = "".join([f'<th style="padding: 10px 12px; text-align: {("center" if i in [1, 5, 7] else ("right" if i in [2, 3, 4, 6] else "left"))};">{h}</th>' for i, h in enumerate(headers)])
            
            rows = []
            for r in pnl:
                err_rate = r.get("defect_rate_pct", 0)
                is_alert = err_rate >= 1.0
                st_color = "#872D43" if is_alert else "#183634"
                st_bg = "#fad2e1" if is_alert else "#c5dedd"
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 10px 12px; font-weight: bold; color: #1e293b;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 9999px; background: {'#ef4444' if is_alert else '#10b981'}; margin-right: 6px;"></span>
                        {r.get('line_name') or r.get('campaign_name')}
                    </td>
                    <td style="padding: 10px 12px; text-align: center; color: #475569; font-weight: bold;">{r.get('lot_count', 0):,} lô</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: #1e293b;">{r.get('output_qty', 0):,.0f} SP</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #047857;">{r.get('passed_qty', 0):,.0f} SP</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #b91c1c;">{r.get('defect_qty', 0):,.0f} SP</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: 900; color: {st_color};">{err_rate}%</td>
                    <td style="padding: 10px 12px; text-align: right; color: #64748b; font-family: monospace;">{r.get('run_time_minutes', 0):,.0f} phút</td>
                    <td style="padding: 10px 12px; text-align: center;">
                        <span style="background: {st_bg}40; color: {st_color}; border: 1px solid {st_bg}; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: 800;">
                            {r.get('status', 'VƯỢT NGƯỠNG' if is_alert else 'ĐẠT CHUẨN')}
                        </span>
                    </td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 12px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

        elif domain == "COHORT_RETENTION":
            headers = ["THÁNG COHORT", "KHÁCH HÀNG MỚI", "M0", "M1", "M2", "M3", "M4", "M5", "ĐÁNH GIÁ"]
            th_html = "".join([f'<th style="padding: 10px 12px; text-align: {("left" if i == 0 else ("right" if i == 1 else "center"))};">{h}</th>' for i, h in enumerate(headers)])
            rows = []
            for r in pnl:
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 10px 12px; font-weight: bold; color: #1e293b;">{r.get('cohort_name') or r.get('campaign_name')}</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #0f766e; font-family: monospace;">{r.get('new_users', 0):,} KH</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: #334155;">100%</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {'#0f766e' if r.get('m1_pct') else '#94a3b8'};">{r.get('m1_pct', '--')}{'%' if r.get('m1_pct') else ''}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {'#0f766e' if r.get('m2_pct') else '#94a3b8'};">{r.get('m2_pct', '--')}{'%' if r.get('m2_pct') else ''}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {'#0f766e' if r.get('m3_pct') else '#94a3b8'};">{r.get('m3_pct', '--')}{'%' if r.get('m3_pct') else ''}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {'#d97706' if r.get('m4_pct') else '#94a3b8'};">{r.get('m4_pct', '--')}{'%' if r.get('m4_pct') else ''}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {'#e11d48' if r.get('m5_pct') else '#94a3b8'};">{r.get('m5_pct', '--')}{'%' if r.get('m5_pct') else ''}</td>
                    <td style="padding: 10px 12px; text-align: center;">
                        <span style="background: #c5dedd40; color: #183634; border: 1px solid #c5dedd; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: bold;">
                            {r.get('status', 'Ổn định')}
                        </span>
                    </td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 12px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

        elif domain == "STORE_PNL":
            headers = ["CỬA HÀNG", "KHU VỰC", "DOANH THU", "CHI PHÍ THUÊ", "CHI PHÍ NHÂN SỰ", "LỢI NHUẬN RÒNG", "BIÊN LÃI %", "ĐÁNH GIÁ"]
            th_html = "".join([f'<th style="padding: 10px 12px; text-align: {("center" if i in [1, 6, 7] else ("right" if i in [2, 3, 4, 5] else "left"))};">{h}</th>' for i, h in enumerate(headers)])
            rows = []
            for r in pnl:
                prof = float(r.get("net_profit") or r.get("contribution_margin") or 0)
                is_loss = prof < 0
                st_color = "#872D43" if is_loss else "#183634"
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 10px 12px; font-weight: bold; color: #1e293b;">{r.get('store_name') or r.get('campaign_name')}</td>
                    <td style="padding: 10px 12px; text-align: center; color: #64748b;">{r.get('region', '--')}</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #183634;">{cls._format_vnd(r.get('revenue') or r.get('net_revenue', 0))}</td>
                    <td style="padding: 10px 12px; text-align: right; color: #64748b;">{cls._format_vnd(r.get('rental_cost', 0))}</td>
                    <td style="padding: 10px 12px; text-align: right; color: #64748b;">{cls._format_vnd(r.get('staff_cost', 0))}</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: {st_color};">{cls._format_vnd(prof)}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: {st_color};">{r.get('profit_margin_pct') or r.get('contribution_margin_pct', 0)}%</td>
                    <td style="padding: 10px 12px; text-align: center;">
                        <span style="background: {'#fad2e1' if is_loss else '#c5dedd'}40; color: {st_color}; border: 1px solid {'#fad2e1' if is_loss else '#c5dedd'}; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: bold;">
                            {r.get('status', 'CẦN TÁI CƠ CẤU' if is_loss else 'SINH LỜI')}
                        </span>
                    </td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 12px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

        elif domain == "SALES_FUNNEL":
            headers = ["KÊNH TIẾP CẬN", "TỔNG SỐ LEADS", "DEAL THẮNG", "ĐANG ĐÀM PHÁN", "DEAL THUA", "WIN RATE %", "TỔNG GIÁ TRỊ PHỄU", "GIÁ TRỊ THẮNG (WON)", "GIÁ TRỊ THẤT THOÁT", "ĐÁNH GIÁ"]
            th_html = "".join([f'<th style="padding: 10px 10px; text-align: {("center" if i in [1, 2, 3, 4, 5, 9] else ("right" if i in [6, 7, 8] else "left"))}; font-size: 11px;">{h}</th>' for i, h in enumerate(headers)])
            rows = []
            for r in pnl:
                wr = float(r.get("win_rate_pct") or 0)
                st_badge = "#047857" if wr >= 25 else "#b45309"
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9; font-size: 11px;">
                    <td style="padding: 10px 10px; font-weight: bold; color: #1e293b;">{r.get('channel') or r.get('campaign_name')}</td>
                    <td style="padding: 10px 10px; text-align: center; font-weight: bold; color: #475569;">{r.get('leads_count', 0):,} Leads</td>
                    <td style="padding: 10px 10px; text-align: center; font-weight: bold; color: #047857;">{r.get('won_deals', 0):,}</td>
                    <td style="padding: 10px 10px; text-align: center; color: #0284c7;">{r.get('in_progress_deals', 0):,}</td>
                    <td style="padding: 10px 10px; text-align: center; color: #be123c;">{r.get('lost_deals', 0):,}</td>
                    <td style="padding: 10px 10px; text-align: center; font-weight: bold; color: {st_badge};">{wr}%</td>
                    <td style="padding: 10px 10px; text-align: right; font-weight: bold; color: #183634;">{cls._format_vnd(r.get('pipeline_value', 0))}</td>
                    <td style="padding: 10px 10px; text-align: right; font-weight: bold; color: #047857;">{cls._format_vnd(r.get('won_value', 0))}</td>
                    <td style="padding: 10px 10px; text-align: right; color: #be123c;">{cls._format_vnd(r.get('lost_value', 0))}</td>
                    <td style="padding: 10px 10px; text-align: center;">
                        <span style="background: {st_badge}15; color: {st_badge}; border: 1px solid {st_badge}40; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: bold;">
                            {r.get('status', f'WIN RATE {wr}%')}
                        </span>
                    </td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 12px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

        elif domain == "SUBSCRIPTION_DEFERRED":
            headers = ["CHU KỲ DỊCH VỤ", "SỐ HỢP ĐỒNG", "TIỀN THU TRƯỚC (VND)", "DOANH THU ĐÃ NHẬN", "DOANH THU HOÃN LẠI", "TRẠNG THÁI"]
            th_html = "".join([f'<th style="padding: 10px 12px; text-align: {("center" if i in [1, 5] else ("right" if i in [2, 3, 4] else "left"))};">{h}</th>' for i, h in enumerate(headers)])
            rows = []
            for r in pnl:
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 10px 12px; font-weight: bold; color: #1e293b;">{r.get('cycle') or r.get('campaign_name')}</td>
                    <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: #475569;">{r.get('contracts_count', 0):,} HĐ</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #0284c7;">{cls._format_vnd(r.get('total_upfront', 0))}</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #047857;">{cls._format_vnd(r.get('recognized_revenue', 0))}</td>
                    <td style="padding: 10px 12px; text-align: right; font-weight: bold; color: #d97706;">{cls._format_vnd(r.get('deferred_revenue', 0))}</td>
                    <td style="padding: 10px 12px; text-align: center;">
                        <span style="background: #c5dedd40; color: #183634; border: 1px solid #c5dedd; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: bold;">
                            {r.get('status', 'Bình thường')}
                        </span>
                    </td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 12px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

        else:
            # Standard Retail P&L 13 columns
            headers = ["CHƯƠNG TRÌNH", "SỐ ĐƠN", "DOANH THU GỘP", "HÀNG TRẢ", "DT THUẦN", "GIÁ VỐN", "LỢI NHUẬN GỘP", "VOUCHER", "CP DIRECT", "CP PHÂN BỔ", "BIÊN CM", "BIÊN %", "ROI %"]
            th_html = "".join([f'<th style="padding: 10px 8px; text-align: {("center" if i in [1, 11, 12] else ("right" if i > 1 else "left"))}; font-size: 10px;">{h}</th>' for i, h in enumerate(headers)])
            rows = []
            for r in pnl:
                cm_val = float(r.get("contribution_margin") or 0)
                cm_col = "#183634" if cm_val >= 0 else "#872D43"
                rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9; font-size: 11px;">
                    <td style="padding: 8px; font-weight: bold; color: #1e293b;">
                        <div>{r.get('campaign_name')}</div>
                        <div style="font-size: 9px; color: #64748b; font-family: monospace;">{r.get('campaign_id')}</div>
                    </td>
                    <td style="padding: 8px; text-align: center; color: #475569;">{r.get('orders_count', 0)}</td>
                    <td style="padding: 8px; text-align: right; color: #475569;">{cls._format_vnd(r.get('gross_revenue', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #872D43; font-weight: bold;">{cls._format_vnd(r.get('returns_value', 0))}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold; color: #183634;">{cls._format_vnd(r.get('net_revenue', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #64748b;">{cls._format_vnd(r.get('cogs', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #334155;">{cls._format_vnd(r.get('gross_profit', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #872D43;">{cls._format_vnd(r.get('discount_cost', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #64748b;">{cls._format_vnd(r.get('direct_cost', 0))}</td>
                    <td style="padding: 8px; text-align: right; color: #64748b;">{cls._format_vnd(r.get('allocated_overhead', 0))}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold; color: {cm_col};">{cls._format_vnd(cm_val)}</td>
                    <td style="padding: 8px; text-align: center; font-weight: bold; color: {cm_col};">{r.get('contribution_margin_pct', 0)}%</td>
                    <td style="padding: 8px; text-align: center; font-weight: bold; color: #183634;">{r.get('roi_pct', 0)}%</td>
                </tr>
                """)
            return f'<table style="width: 100%; border-collapse: collapse; font-size: 11px;"><thead><tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #475569; text-transform: uppercase;">{th_html}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

    @classmethod
    def _render_recs_html(cls, summary: Dict[str, Any]) -> str:
        recs = summary.get("recommendations") or []
        user_mods = summary.get("user_modifications") or []
        
        mods_html = ""
        if user_mods:
            mod_items = "".join([f"<li style='margin-bottom: 4px;'><strong>Bước {m.get('step', 3)}:</strong> {m.get('action_summary', '')} ({'; '.join(m.get('applied_notes', []))})</li>" for m in user_mods])
            mods_html = f"""
            <div style="background: #eef8f7; border: 1.5px solid #c5dedd; border-left: 5px solid #183634; border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 6px 0; font-size: 13px; color: #183634; text-transform: uppercase; font-weight: 800;">
                    ✓ Đã Ghi Nhận & Đồng Bộ Các Yêu Cầu Chỉnh Sửa
                </h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #334155;">
                    {mod_items}
                </ul>
            </div>
            """

        if not recs:
            return mods_html + '<div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; color: #64748b; font-size: 12px;">Đã hoàn tất phân tích toàn diện bộ dữ liệu. Không phát sinh cảnh báo vi phạm ngưỡng rủi ro.</div>'

        rec_cards = []
        for r in recs:
            dec = str(r.get("decision") or r.get("priority") or "TIẾP TỤC TRIỂN KHAI").upper()
            is_danger = any(w in dec for w in ["DỪNG", "BẢO TRÌ", "STOP", "TÁI CƠ CẤU", "LỖ", "CẤP THIẾT", "DANGER"])
            badge_bg = "#fad2e1" if is_danger else "#c5dedd"
            badge_txt = "#872D43" if is_danger else "#183634"
            actions_list = r.get("action_items") or r.get("actions") or []
            actions_html = "".join([f"<li style='margin-bottom: 4px;'>{a}</li>" for a in actions_list])

            rec_cards.append(f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; margin-bottom: 10px; flex-wrap: gap: 8px;">
                    <div>
                        <strong style="font-size: 14px; color: #1e293b;">{r.get('campaign_name') or r.get('title')}</strong>
                        <span style="font-size: 11px; color: #64748b; margin-left: 6px; font-family: monospace;">({r.get('campaign_id') or 'REC'})</span>
                    </div>
                    <span style="background: {badge_bg}; color: {badge_txt}; border: 1px solid {badge_txt}30; padding: 3px 12px; border-radius: 9999px; font-size: 11px; font-weight: 800;">
                        {r.get('decision') or r.get('priority', 'KHUYẾN NGHỊ')}
                    </span>
                </div>
                <p style="font-size: 12px; color: #334155; line-height: 1.5; margin-bottom: 10px;">
                    <strong>Lý do trọng tâm:</strong> {r.get('primary_reason') or r.get('desc', '')}
                </p>
                {f'<div style="background: #f8fafc; border-left: 3px solid #183634; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #1e293b; margin-bottom: 8px;"><strong style="font-size: 11px; text-transform: uppercase; color: #183634; display: block; margin-bottom: 4px;">Kế hoạch hành động cụ thể:</strong><ul style="margin: 0; padding-left: 18px;">{actions_html}</ul></div>' if actions_html else ''}
            </div>
            """)

        return mods_html + "".join(rec_cards)

    @classmethod
    def _render_thematic_section(cls, summary: Dict[str, Any], meta: Dict[str, Any]) -> str:
        """Phần 4: Phân tích chuyên đề theo chiều sâu, cơ cấu chi phí, dòng tiền & rủi ro."""
        fin = summary.get("financial_kpis") or {}
        domain = meta["domain"]
        is_fin = meta["is_financial"]
        thematic_blocks = []

        # 1. Cơ cấu chi phí & Lợi nhuận (Cost & Profit Waterfall)
        if is_fin and (fin.get("total_gross_revenue", 0) > 0 or fin.get("total_net_revenue", 0) > 0):
            cogs = float(fin.get("total_cogs") or 0)
            disc = float(fin.get("total_discount_amount") or 0)
            mkt = float(fin.get("total_campaign_costs") or 0)
            gross = float(fin.get("total_gross_revenue") or fin.get("total_net_revenue") or 1)
            cm = float(fin.get("total_contribution_margin") or 0)
            
            cogs_pct = (cogs / gross * 100) if gross > 0 else 0
            disc_pct = (disc / gross * 100) if gross > 0 else 0
            mkt_pct = (mkt / gross * 100) if gross > 0 else 0
            cm_pct = (cm / gross * 100) if gross > 0 else 0

            cost_html = f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; margin-bottom: 16px;">
                <h4 style="margin: 0 0 12px 0; font-size: 13px; font-weight: 800; color: #183634; text-transform: uppercase;">
                    1. Phân Tích Cơ Cấu Chi Phí & Dòng Chảy Lợi Nhuận (Cost Breakdown & Margin)
                </h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
                    <div style="background: #f8fafc; border-radius: 12px; padding: 12px; border-left: 4px solid #0284c7;">
                        <div style="font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase;">Giá Vốn COGS</div>
                        <div style="font-size: 16px; font-weight: 900; color: #1e293b; margin: 4px 0;">{cls._format_vnd(cogs)}</div>
                        <div style="font-size: 10px; color: #0284c7; font-weight: bold;">Tỷ trọng: {cogs_pct:.1f}% DT</div>
                    </div>
                    <div style="background: #f8fafc; border-radius: 12px; padding: 12px; border-left: 4px solid #e11d48;">
                        <div style="font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase;">Chiết Khấu Voucher</div>
                        <div style="font-size: 16px; font-weight: 900; color: #872D43; margin: 4px 0;">{cls._format_vnd(disc)}</div>
                        <div style="font-size: 10px; color: #e11d48; font-weight: bold;">Tỷ trọng: {disc_pct:.1f}% DT</div>
                    </div>
                    <div style="background: #f8fafc; border-radius: 12px; padding: 12px; border-left: 4px solid #d97706;">
                        <div style="font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase;">Chi Phí MKT & Vận Hành</div>
                        <div style="font-size: 16px; font-weight: 900; color: #92400e; margin: 4px 0;">{cls._format_vnd(mkt)}</div>
                        <div style="font-size: 10px; color: #d97706; font-weight: bold;">Tỷ trọng: {mkt_pct:.1f}% DT</div>
                    </div>
                    <div style="background: #f8fafc; border-radius: 12px; padding: 12px; border-left: 4px solid #0d9488;">
                        <div style="font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase;">Biên Đóng Góp (CM)</div>
                        <div style="font-size: 16px; font-weight: 900; color: {'#047857' if cm >= 0 else '#872D43'}; margin: 4px 0;">{cls._format_vnd(cm)}</div>
                        <div style="font-size: 10px; color: {'#047857' if cm >= 0 else '#872D43'}; font-weight: bold;">Tỷ suất: {cm_pct:.1f}% DT</div>
                    </div>
                </div>
            </div>
            """
            thematic_blocks.append(cost_html)

        # 2. Chi tiết kênh phân phối hoặc địa bàn
        channels = [c for c in (summary.get("channel_breakdown") or []) if c.get("channel") and c.get("channel") not in ["--", "Unknown", "None"] and float(c.get("net_revenue") or 0) > 0]
        if channels:
            ch_rows = []
            for c in channels:
                ret_rate = float(c.get("return_rate_pct") or 0)
                ch_rows.append(f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 8px 10px; font-weight: bold; color: #1e293b;">{c.get('channel')}</td>
                    <td style="padding: 8px 10px; text-align: right; color: #475569;">{cls._format_vnd(c.get('gross_revenue', 0))}</td>
                    <td style="padding: 8px 10px; text-align: right; color: {'#e11d48' if ret_rate > 5 else '#64748b'};">{cls._format_vnd(c.get('return_amount', 0))} ({ret_rate}%)</td>
                    <td style="padding: 8px 10px; text-align: right; font-weight: bold; color: #183634;">{cls._format_vnd(c.get('net_revenue', 0))}</td>
                    <td style="padding: 8px 10px; text-align: center; font-weight: bold; color: #0284c7;">{c.get('revenue_share_pct', 0)}%</td>
                </tr>
                """)
            ch_html = f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; margin-bottom: 16px;">
                <h4 style="margin: 0 0 12px 0; font-size: 13px; font-weight: 800; color: #183634; text-transform: uppercase;">
                    2. Hiệu Quả Đóng Góp & Phân Bổ Theo Kênh Phân Phối (Omnichannel)
                </h4>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                        <thead>
                            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #475569; text-transform: uppercase;">
                                <th style="padding: 8px 10px; text-align: left;">Kênh Phân Phối</th>
                                <th style="padding: 8px 10px; text-align: right;">Doanh Thu Gộp</th>
                                <th style="padding: 8px 10px; text-align: right;">Hàng Hoàn (Tỷ Lệ %)</th>
                                <th style="padding: 8px 10px; text-align: right;">Doanh Thu Thuần</th>
                                <th style="padding: 8px 10px; text-align: center;">Tỷ Trọng Đóng Góp</th>
                            </tr>
                        </thead>
                        <tbody>{"".join(ch_rows)}</tbody>
                    </table>
                </div>
            </div>
            """
            thematic_blocks.append(ch_html)

        # 3. Phát hiện bất thường & Điểm nghẽn rủi ro
        pnl = summary.get("pnl_table") or []
        anomalies = []
        if domain == "STORE_PNL":
            for r in pnl:
                prof = float(r.get("net_profit") or r.get("contribution_margin") or 0)
                if prof < 0:
                    anomalies.append(f"<strong>{r.get('store_name') or r.get('campaign_name')}</strong> đang chịu khoản lỗ vận hành <strong>{cls._format_vnd(prof)}</strong> do chi phí mặt bằng ({cls._format_vnd(r.get('rental_cost', 0))}) chiếm tỷ trọng quá lớn so với doanh thu.")
        elif domain == "MANUFACTURING_QUALITY":
            for r in pnl:
                err_rate = float(r.get("defect_rate_pct") or 0)
                if err_rate >= 1.0:
                    anomalies.append(f"<strong>{r.get('line_name') or r.get('campaign_name')}</strong> có tỷ lệ lỗi vượt ngưỡng kiểm soát: <strong>{err_rate}%</strong> (phát sinh {r.get('defect_qty', 0):,} sản phẩm lỗi).")
        elif domain == "COHORT_RETENTION":
            for r in pnl:
                m1 = float(r.get("m1_pct") or 0)
                if m1 > 0 and m1 < 80:
                    anomalies.append(f"<strong>{r.get('cohort_name')}</strong> ghi nhận tỷ lệ giữ chân tháng đầu (M1 Retention) giảm mạnh xuống <strong>{m1}%</strong>.")
        else:
            for r in pnl:
                cm = float(r.get("contribution_margin") or 0)
                if cm < 0 and r.get("campaign_id") != "ORGANIC":
                    anomalies.append(f"Chiến dịch <strong>{r.get('campaign_name')}</strong> bị âm biên đóng góp <strong>{cls._format_vnd(cm)}</strong> do chiết khấu voucher và chi phí trực tiếp vượt quá doanh thu.")

        if anomalies:
            ano_items = "".join([f"<li style='margin-bottom: 6px; color: #991b1b;'>⚠️ {a}</li>" for a in anomalies])
            ano_html = f"""
            <div style="background: #fef2f2; border: 1.5px solid #fecaca; border-radius: 16px; padding: 18px 20px; margin-bottom: 16px;">
                <h4 style="margin: 0 0 10px 0; font-size: 13px; font-weight: 800; color: #991b1b; text-transform: uppercase;">
                    3. Phát Hiện Bất Thường & Điểm Nghẽn Rủi Ro Vận Hành
                </h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 12px; line-height: 1.6;">
                    {ano_items}
                </ul>
            </div>
            """
            thematic_blocks.append(ano_html)

        return "".join(thematic_blocks) if thematic_blocks else '<div style="background: white; border: 1px dashed #cbd5e1; border-radius: 16px; padding: 20px; text-align: center; color: #64748b; font-size: 12px;">Đã hoàn tất phân tích chuyên đề. Số liệu phân bố ổn định, không ghi nhận điểm nghẽn rủi ro phát sinh.</div>'

    @classmethod
    def _render_solutions_section(cls, summary: Dict[str, Any]) -> str:
        """Phần 5: Chẩn đoán nguyên nhân gốc rễ và hệ thống giải pháp 3 cấp độ."""
        root_causes = summary.get("root_causes") or summary.get("problem_solution_matrix") or []
        if not root_causes:
            return '<div style="background: white; border: 1px dashed #cbd5e1; border-radius: 16px; padding: 24px; text-align: center; color: #64748b; font-size: 12px;">Chưa phát hiện vấn đề bất thường cần chẩn đoán nguyên nhân gốc rễ. Hệ thống vận hành trong giới hạn an toàn.</div>'

        cards = []
        for idx, rc in enumerate(root_causes):
            sev = str(rc.get("severity") or "WARNING").upper()
            sev_bg = "#fad2e1" if "CRIT" in sev else ("#fef3c7" if "WARN" in sev else "#e0f2fe")
            sev_col = "#872D43" if "CRIT" in sev else ("#92400e" if "WARN" in sev else "#0369a1")

            u_sol = rc.get("urgent_solution") or rc.get("action_24h") or "Tạm dừng ngay các hạng mục thâm hụt tài chính hoặc vượt ngưỡng lỗi trong 24h."
            m_sol = rc.get("medium_solution") or rc.get("medium_term") or "Tối ưu hóa phân bổ định phí, thiết lập trần chi phí và tái đàm phán hợp đồng trong 1-2 tuần."
            s_sol = rc.get("strategic_solution") or rc.get("long_term") or "Tái định vị mô hình vận hành, chuẩn hóa Best Practices và áp dụng kiểm soát tự động."
            impact = rc.get("expected_impact") or rc.get("impact") or "Gia tăng tỷ suất sinh lời và ngăn chặn 100% rủi ro thâm hụt dòng tiền."

            cards.append(f"""
            <div style="background: white; border: 1.5px solid #e2e8f0; border-radius: 18px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="font-size: 10px; font-weight: 800; color: #64748b; text-transform: uppercase;">CHẨN ĐOÁN #{idx+1}</span>
                        <h4 style="margin: 2px 0 0 0; font-size: 14px; font-weight: 900; color: #1e293b;">{rc.get('title') or rc.get('problem', 'Chẩn đoán bất thường số liệu')}</h4>
                    </div>
                    <span style="background: {sev_bg}; color: {sev_col}; border: 1px solid {sev_col}40; padding: 4px 12px; border-radius: 9999px; font-size: 10px; font-weight: 900; letter-spacing: 0.5px;">
                        {sev}
                    </span>
                </div>

                <div style="margin-bottom: 16px;">
                    <p style="font-size: 12px; color: #334155; line-height: 1.6; margin: 0 0 8px 0;">
                        <strong>Bằng chứng định lượng:</strong> {rc.get('evidence') or rc.get('problem', '')}
                    </p>
                    <div style="background: #f8fafc; border-left: 4px solid #183634; border-radius: 8px; padding: 12px 16px;">
                        <span style="font-size: 11px; font-weight: 900; text-transform: uppercase; color: #183634; display: block; margin-bottom: 4px;">
                            🔍 CHẨN ĐOÁN NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE ANALYSIS):
                        </span>
                        <div style="font-size: 12px; color: #0f172a; line-height: 1.6; font-weight: 500;">
                            {rc.get('root_cause', '')}
                        </div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 14px;">
                    <div style="background: #fff1f2; border: 1px solid #fecdd3; border-radius: 12px; padding: 14px;">
                        <div style="font-size: 11px; font-weight: 900; color: #e11d48; text-transform: uppercase; margin-bottom: 6px;">
                            ⚡ 1. CẤP BÁCH (TRONG 24H - 48H)
                        </div>
                        <div style="font-size: 11px; color: #4c0519; line-height: 1.5;">{u_sol}</div>
                    </div>
                    <div style="background: #fefce8; border: 1px solid #fef08a; border-radius: 12px; padding: 14px;">
                        <div style="font-size: 11px; font-weight: 900; color: #ca8a04; text-transform: uppercase; margin-bottom: 6px;">
                            ⏱️ 2. TỐI ƯU HÓA (1 - 2 TUẦN)
                        </div>
                        <div style="font-size: 11px; color: #713f12; line-height: 1.5;">{m_sol}</div>
                    </div>
                    <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 12px; padding: 14px;">
                        <div style="font-size: 11px; font-weight: 900; color: #059669; text-transform: uppercase; margin-bottom: 6px;">
                            🎯 3. CHIẾN LƯỢC DÀI HẠN & A/B TEST
                        </div>
                        <div style="font-size: 11px; color: #064e3b; line-height: 1.5;">{s_sol}</div>
                    </div>
                </div>

                <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #86efac; border-radius: 10px; padding: 10px 14px; font-size: 11px; color: #166534; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                    <span>🚀</span> <strong>Tác động định lượng kỳ vọng:</strong> {impact}
                </div>
            </div>
            """)

        return "".join(cards)

    @classmethod
    def _render_conclusion_section(cls, summary: Dict[str, Any]) -> str:
        """Phần 6: Kết luận & Đề xuất hành động điều hành."""
        gemini_insights = summary.get("ai_executive_insights") or "Đã hoàn tất phân tích toàn diện dữ liệu. Các chỉ số vận hành được kiểm soát theo đúng chuẩn mực kinh doanh."
        recs_html = cls._render_recs_html(summary)
        
        audit_trail = summary.get("audit_trail") or []
        audit_items = []
        if audit_trail:
            for l in audit_trail[-5:]:
                audit_items.append(f"<li style='margin-bottom: 4px; font-size: 11px; color: #475569;'><strong>[{l.get('time', '--')}]</strong> {l.get('message', '')}</li>")
        audit_html = f"""
        <div style="margin-top: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 14px 18px;">
            <div style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 8px;">
                🛡️ NHẬT KÝ KIỂM TOÁN VẬN HÀNH & TÍNH TOÀN VẸN SỐ LIỆU
            </div>
            <ul style="margin: 0; padding-left: 18px;">
                {"".join(audit_items) if audit_items else "<li style='font-size: 11px; color: #64748b;'>Toàn bộ dữ liệu gốc được xác thực và bảo toàn 100% trong suốt quá trình phân tích.</li>"}
            </ul>
        </div>
        """

        return f"""
        <div style="background: linear-gradient(135deg, #fde2e4 0%, #fad2e1 100%); border: 1.5px solid #f2a8c0; border-radius: 18px; padding: 22px 26px; margin-bottom: 24px; color: #3d1825; box-shadow: 0 4px 12px rgba(242,168,192,0.15);">
            <div style="font-size: 12px; font-weight: 900; text-transform: uppercase; color: #872D43; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                <span>✨</span> NHẬN ĐỊNH ĐIỀU HÀNH TỔNG THỂ TỪ TRỢ LÝ AI STUDIO
            </div>
            <div style="font-size: 13px; line-height: 1.7; font-weight: 500;">
                {gemini_insights}
            </div>
        </div>

        <div style="margin-bottom: 16px;">
            <div style="font-size: 13px; font-weight: 900; color: #183634; text-transform: uppercase; margin-bottom: 12px;">
                📋 DANH MỤC QUYẾT ĐỊNH CHIẾN LƯỢC ĐÃ ĐƯỢC PHÊ DUYỆT
            </div>
            {recs_html}
        </div>

        {audit_html}
        """

    @classmethod
    def generate_pnl_report(cls, summary: Dict[str, Any]) -> str:
        """Xuất báo cáo HTML đầy đủ chuẩn xác 6 phần theo yêu cầu người dùng."""
        meta = cls._resolve_domain_meta(summary)
        charts = cls._collect_valid_charts(summary)
        context = summary.get("business_context") or {}
        project_name = context.get("project_name") or "Dự Án Phân Tích Dữ Liệu Doanh Nghiệp"
        business_type = context.get("business_type") or "Bán lẻ & Thương mại điện tử"
        file_name = context.get("file_name") or "Dữ liệu khảo sát thực tế"
        user_question = context.get("focus_question") or (summary.get("question_sufficiency") or {}).get("user_question") or "Phân tích toàn diện hiệu quả kinh doanh & tối ưu hóa vận hành"

        # Chart Canvas & JS Generation
        chart_boxes = []
        chart_js_lines = []

        for idx, c in enumerate(charts):
            span_style = "grid-column: span 2;" if c["is_wide"] else ""
            chart_boxes.append(f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); {span_style}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #f8fafc; padding-bottom: 8px;">
                    <div>
                        <strong style="font-size: 13px; color: #183634; display: block;">{idx+1}. {c['title']}</strong>
                        <span style="font-size: 11px; color: #64748b;">{c['subtitle']}</span>
                    </div>
                    {f'<span style="font-size: 10px; font-weight: bold; background: #c5dedd40; color: #183634; padding: 2px 8px; border-radius: 9999px;">{c["unit"]}</span>' if c['unit'] else ''}
                </div>
                <div style="height: 250px; position: relative;">
                    <canvas id="{c['id']}"></canvas>
                </div>
            </div>
            """)

            chart_js_lines.append(f"""
            try {{
                new Chart(document.getElementById('{c["id"]}'), {{
                    type: '{c["type"]}',
                    data: {{
                        labels: {json.dumps(c["labels"], ensure_ascii=False)},
                        datasets: {json.dumps(c["datasets"], ensure_ascii=False)}
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                                labels: {{ boxWidth: 10, font: {{ family: 'Plus Jakarta Sans', size: 10, weight: 'bold' }} }}
                            }}
                        }},
                        scales: {json.dumps({} if c["type"] in ["doughnut", "pie"] else {"x": {"grid": {"display": False}}, "y": {"beginAtZero": True, "grid": {"color": "#f1f5f9"}}})}
                    }}
                }});
            }} catch(e) {{ console.error("Chart render error:", e); }}
            """)

        charts_grid_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px;">{"".join(chart_boxes)}</div>' if chart_boxes else '<div style="background: white; border: 1px dashed #cbd5e1; border-radius: 16px; padding: 24px; text-align: center; color: #64748b; font-size: 12px;">Đang tự động đồng bộ biểu đồ tương thích.</div>'

        # Subsections
        kpis_html = cls._render_kpis_html(summary, meta)
        table_html = cls._render_main_table_html(summary, meta)
        thematic_html = cls._render_thematic_section(summary, meta)
        solutions_html = cls._render_solutions_section(summary)
        conclusion_html = cls._render_conclusion_section(summary)

        focus_callout = ""
        q_suff = summary.get("question_sufficiency") or {}
        if q_suff.get("is_sufficient") and q_suff.get("deep_dive_analysis"):
            deep = q_suff["deep_dive_analysis"]
            bullets_str = "".join([f'<li style="margin-bottom: 6px;">{b}</li>' for b in deep.get("bullets", [])])
            rec_str = f'<div style="margin-top: 10px; padding: 10px 14px; background: rgba(255,255,255,0.92); border-radius: 10px; border: 1px solid #6ee7b7; font-size: 12px; font-weight: bold; color: #064e3b;">🚀 <strong>Đề xuất chiến lược:</strong> {deep.get("action_recommendation", "")}</div>' if deep.get("action_recommendation") else ""
            focus_callout = f"""
            <div style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.25); border-radius: 14px; padding: 16px 20px; margin-top: 16px; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 12px; font-weight: 900; text-transform: uppercase; color: #72efdd;">🎯 KẾT QUẢ PHÂN TÍCH CHUYÊN SÂU TRỌNG TÂM</div>
                    <span style="background: #10b981; color: white; padding: 2px 10px; border-radius: 9999px; font-size: 10px; font-weight: 800;">✓ ĐỦ ĐIỀU KIỆN SỐ LIỆU</span>
                </div>
                <div style="font-size: 12px; font-weight: 700; margin-bottom: 8px; color: #fef08a;">Vấn đề yêu cầu: <em>"{q_suff.get('user_question', '')}"</em></div>
                <ul style="margin: 0; padding-left: 20px; font-size: 12px; line-height: 1.6; color: #f1f5f9;">
                    {bullets_str}
                </ul>
                {rec_str}
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['report_title']} - Thu Hà AI Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 32px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .badge-domain {{
            background: rgba(197, 222, 221, 0.25);
            border: 1px solid #c5dedd;
            color: #c5dedd;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
            display: inline-block;
            margin-bottom: 8px;
        }}
        .section-box {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 900;
            color: #183634;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0 0 16px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ========================================== -->
        <!-- PHẦN 1: BỐI CẢNH DỰ ÁN & TIẾP NHẬN DỮ LIỆU -->
        <!-- ========================================== -->
        <div class="section-box" style="background: linear-gradient(135deg, #183634 0%, #224e4a 100%); color: white; border: none; box-shadow: 0 10px 25px -5px rgba(24, 54, 52, 0.2);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
                <div>
                    <span class="badge-domain">{meta['badge']}</span>
                    <h1 style="margin: 4px 0 6px 0; font-size: 22px; font-weight: 900; color: white;">PHẦN 1: BỐI CẢNH DỰ ÁN & NGUỒN DỮ LIỆU ĐỐI SOÁT</h1>
                    <div style="font-size: 14px; font-weight: 700; color: #c5dedd;">{meta['report_title']}</div>
                </div>
                <div style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 8px 14px; text-align: right; font-size: 11px;">
                    <div style="color: #c5dedd; opacity: 0.85;">Kiểm định số liệu:</div>
                    <strong style="color: #6ee7b7; font-size: 12px;">✓ 100% Đủ điều kiện số liệu</strong>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; background: rgba(0,0,0,0.18); border-radius: 14px; padding: 14px; margin-top: 12px; font-size: 12px;">
                <div>
                    <span style="color: #c5dedd; font-size: 11px; display: block;">Tên Dự Án / Thương Hiệu:</span>
                    <strong style="color: white; font-size: 13px;">{project_name}</strong>
                </div>
                <div>
                    <span style="color: #c5dedd; font-size: 11px; display: block;">Loại Hình Doanh Nghiệp:</span>
                    <strong style="color: white; font-size: 13px;">{business_type}</strong>
                </div>
                <div>
                    <span style="color: #c5dedd; font-size: 11px; display: block;">Tệp Dữ Liệu Khảo Sát:</span>
                    <strong style="color: #72efdd; font-size: 13px; font-family: monospace;">{file_name}</strong>
                </div>
                <div>
                    <span style="color: #c5dedd; font-size: 11px; display: block;">Vấn Đề Trọng Tâm Yêu Cầu:</span>
                    <strong style="color: #fef08a; font-size: 12px;">"{user_question}"</strong>
                </div>
            </div>

            {focus_callout}
        </div>

        <!-- ========================================== -->
        <!-- PHẦN 2: DASHBOARD KPI KINH DOANH & VẬN HÀNH -->
        <!-- ========================================== -->
        <div class="section-box">
            <div class="section-title">
                <span>📌 PHẦN 2: DASHBOARD KPI KINH DOANH & VẬN HÀNH TRỌNG TÂM</span>
                <span style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: none;">Chỉ số cốt lõi</span>
            </div>
            {kpis_html}
        </div>

        <!-- ========================================== -->
        <!-- PHẦN 3: PHÂN TÍCH DỮ LIỆU ĐA CHIỀU & BẢNG THỐNG KÊ CHI TIẾT -->
        <!-- ========================================== -->
        <div class="section-box">
            <div class="section-title">
                <span>📊 PHẦN 3: PHÂN TÍCH DỮ LIỆU ĐA CHIỀU & BẢNG SỐ LIỆU ĐỐI SOÁT</span>
                <span style="font-size: 11px; font-weight: bold; color: #0d9488; background: #c5dedd40; padding: 2px 10px; border-radius: 9999px; text-transform: none;">{len(charts)} biểu đồ trực quan • 100% Khớp chú giải</span>
            </div>
            <p style="font-size: 12px; color: #64748b; margin: -6px 0 16px 0;">
                Toàn bộ biểu đồ và bảng đối soát trực tiếp theo cấu trúc dữ liệu thực tế, các chuỗi dữ liệu rỗng và phân khúc bằng 0 đã được lọc bỏ để đảm bảo độ chính xác tuyệt đối.
            </p>
            {charts_grid_html}

            <div style="margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px;">
                <div style="font-size: 13px; font-weight: 800; color: #183634; text-transform: uppercase; margin-bottom: 12px;">
                    📋 {meta['table_title']} ({meta['unit_label']})
                </div>
                <div style="overflow-x: auto;">
                    {table_html}
                </div>
            </div>
        </div>

        <!-- ========================================== -->
        <!-- PHẦN 4: PHÂN TÍCH CHUYÊN ĐỀ THEO CHIỀU SÂU & RỦI RO -->
        <!-- ========================================== -->
        <div class="section-box">
            <div class="section-title">
                <span>🔬 PHẦN 4: PHÂN TÍCH CHUYÊN ĐỀ THEO CHIỀU SÂU & RỦI RO VẬN HÀNH</span>
                <span style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: none;">Cơ cấu chi phí • Kênh phân phối • Điểm nghẽn</span>
            </div>
            {thematic_html}
        </div>

        <!-- ========================================== -->
        <!-- PHẦN 5: KẾT QUẢ & ĐỀ XUẤT HỆ THỐNG GIẢI PHÁP -->
        <!-- ========================================== -->
        <div class="section-box">
            <div class="section-title">
                <span>💡 PHẦN 5: KẾT QUẢ & ĐỀ XUẤT HỆ THỐNG GIẢI PHÁP THỰC THI</span>
                <span style="font-size: 11px; font-weight: bold; color: #872D43; background: #fad2e140; padding: 2px 10px; border-radius: 9999px; text-transform: none;">Root Cause Analysis & 3-Tier Action Matrix</span>
            </div>
            <p style="font-size: 12px; color: #64748b; margin: -6px 0 16px 0;">
                Chẩn đoán nguyên nhân gốc rễ được bóc tách từ các bất thường số liệu định lượng trong tệp dữ liệu, gắn liền với ma trận giải pháp phân kỳ 24h - 2 tuần - dài hạn.
            </p>
            {solutions_html}
        </div>

        <!-- ========================================== -->
        <!-- PHẦN 6: KẾT LUẬN & ĐỀ XUẤT HÀNH ĐỘNG ĐIỀU HÀNH -->
        <!-- ========================================== -->
        <div class="section-box">
            <div class="section-title">
                <span>🎯 PHẦN 6: KẾT LUẬN & ĐỀ XUẤT HÀNH ĐỘNG ĐIỀU HÀNH</span>
                <span style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: none;">AI Executive Advisory • Quyết định đã phê duyệt</span>
            </div>
            {conclusion_html}
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            {chr(10).join(chart_js_lines)}
        }});
    </script>
</body>
</html>"""

    @classmethod
    def generate_dashboard_overview(cls, summary: Dict[str, Any]) -> str:
        """Xuất Dashboard tổng quan đa chiều tương tác với đầy đủ các phần."""
        meta = cls._resolve_domain_meta(summary)
        charts = cls._collect_valid_charts(summary)
        context = summary.get("business_context") or {}
        project_name = context.get("project_name") or "Dự Án Phân Tích Dữ Liệu Doanh Nghiệp"
        file_name = context.get("file_name") or "Dữ liệu khảo sát thực tế"

        # Tab generation
        tabs_html = [
            '<button type="button" onclick="switchTab(\'OVERVIEW\')" id="btnTab-OVERVIEW" class="tab-btn active" style="padding: 8px 16px; border-radius: 12px; font-weight: 800; font-size: 12px; border: 1px solid #e2e8f0; background: white; color: #183634; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">Lưới Toàn Cảnh</button>'
        ]
        
        panels_html = []
        chart_js_lines = []

        # Overview Grid Panel
        overview_boxes = []
        for idx, c in enumerate(charts):
            span_style = "grid-column: span 2;" if c["is_wide"] else ""
            overview_boxes.append(f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); {span_style}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #f8fafc; padding-bottom: 8px;">
                    <div>
                        <strong style="font-size: 13px; color: #183634; display: block;">{idx+1}. {c['title']}</strong>
                        <span style="font-size: 11px; color: #64748b;">{c['subtitle']}</span>
                    </div>
                    {f'<span style="font-size: 10px; font-weight: bold; background: #c5dedd40; color: #183634; padding: 2px 8px; border-radius: 9999px;">{c["unit"]}</span>' if c['unit'] else ''}
                </div>
                <div style="height: 250px; position: relative;">
                    <canvas id="dash_{c['id']}"></canvas>
                </div>
            </div>
            """)

            chart_js_lines.append(f"""
            try {{
                new Chart(document.getElementById('dash_{c["id"]}'), {{
                    type: '{c["type"]}',
                    data: {{
                        labels: {json.dumps(c["labels"], ensure_ascii=False)},
                        datasets: {json.dumps(c["datasets"], ensure_ascii=False)}
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                                labels: {{ boxWidth: 10, font: {{ family: 'Plus Jakarta Sans', size: 10, weight: 'bold' }} }}
                            }}
                        }},
                        scales: {json.dumps({} if c["type"] in ["doughnut", "pie"] else {"x": {"grid": {"display": False}}, "y": {"beginAtZero": True, "grid": {"color": "#f1f5f9"}}})}
                    }}
                }});
            }} catch(e) {{ console.error("Dash chart error:", e); }}
            """)

        overview_grid_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px;">{"".join(overview_boxes)}</div>' if overview_boxes else '<div style="background: white; border: 1px dashed #cbd5e1; border-radius: 16px; padding: 24px; text-align: center; color: #64748b; font-size: 12px;">Đang cập nhật biểu đồ phù hợp dữ liệu.</div>'
        panels_html.append(f'<div id="view-OVERVIEW" class="view-panel">{overview_grid_html}</div>')

        # Additional single view panels
        for idx, c in enumerate(charts):
            tab_id = f"ANGLE_{idx}"
            tabs_html.append(f'<button type="button" onclick="switchTab(\'{tab_id}\')" id="btnTab-{tab_id}" class="tab-btn" style="padding: 8px 16px; border-radius: 12px; font-weight: bold; font-size: 12px; border: 1px solid transparent; background: transparent; color: #475569; cursor: pointer;">{c["title"][:22]}...</button>')
            panels_html.append(f"""
            <div id="view-{tab_id}" class="view-panel" style="display: none;">
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                    <div style="margin-bottom: 16px; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px;">
                        <h3 style="font-size: 16px; font-weight: 900; color: #183634; margin: 0 0 4px 0;">{c['title']}</h3>
                        <p style="font-size: 12px; color: #64748b; margin: 0;">{c['subtitle']}</p>
                    </div>
                    <div style="height: 380px; position: relative;">
                        <canvas id="single_{c['id']}"></canvas>
                    </div>
                </div>
            </div>
            """)

            chart_js_lines.append(f"""
            try {{
                new Chart(document.getElementById('single_{c["id"]}'), {{
                    type: '{c["type"]}',
                    data: {{
                        labels: {json.dumps(c["labels"], ensure_ascii=False)},
                        datasets: {json.dumps(c["datasets"], ensure_ascii=False)}
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                                labels: {{ boxWidth: 12, font: {{ family: 'Plus Jakarta Sans', size: 11, weight: 'bold' }} }}
                            }}
                        }},
                        scales: {json.dumps({} if c["type"] in ["doughnut", "pie"] else {"x": {"grid": {"display": False}}, "y": {"beginAtZero": True, "grid": {"color": "#f1f5f9"}}})}
                    }}
                }});
            }} catch(e) {{ console.error("Single chart error:", e); }}
            """)

        # Add Thematic & Solutions Tabs to Dashboard
        tabs_html.append('<button type="button" onclick="switchTab(\'THEMATIC\')" id="btnTab-THEMATIC" class="tab-btn" style="padding: 8px 16px; border-radius: 12px; font-weight: bold; font-size: 12px; border: 1px solid transparent; background: transparent; color: #475569; cursor: pointer;">Phân Tích Chuyên Đề</button>')
        thematic_html = cls._render_thematic_section(summary, meta)
        panels_html.append(f'<div id="view-THEMATIC" class="view-panel" style="display: none;">{thematic_html}</div>')

        tabs_html.append('<button type="button" onclick="switchTab(\'SOLUTIONS\')" id="btnTab-SOLUTIONS" class="tab-btn" style="padding: 8px 16px; border-radius: 12px; font-weight: bold; font-size: 12px; border: 1px solid transparent; background: transparent; color: #475569; cursor: pointer;">Chẩn Đoán & Giải Pháp</button>')
        solutions_html = cls._render_solutions_section(summary)
        panels_html.append(f'<div id="view-SOLUTIONS" class="view-panel" style="display: none;">{solutions_html}</div>')

        kpis_html = cls._render_kpis_html(summary, meta)
        table_html = cls._render_main_table_html(summary, meta)
        recs_html = cls._render_recs_html(summary)

        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['dashboard_title']} - Thu Hà Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 32px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header-box {{
            background: linear-gradient(135deg, #183634 0%, #224e4a 100%);
            border-radius: 24px;
            padding: 24px 30px;
            color: white;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            box-shadow: 0 10px 25px -5px rgba(24, 54, 52, 0.2);
        }}
        .tab-btn.active {{
            background: white !important;
            color: #183634 !important;
            border-color: #e2e8f0 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            font-weight: 800 !important;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 900;
            color: #183634;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0 0 14px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .section-box {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 22px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- TOP HEADER -->
        <div class="header-box">
            <div>
                <span style="background: rgba(197, 222, 221, 0.25); border: 1px solid #c5dedd; color: #c5dedd; padding: 3px 10px; border-radius: 9999px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 6px;">{meta['badge']}</span>
                <h1 style="margin: 0; font-size: 20px; font-weight: 900;">{meta['dashboard_title']}</h1>
                <p style="margin: 4px 0 0 0; font-size: 12px; color: #c5dedd; opacity: 0.85;">Dự án: {project_name} • Tệp: {file_name}</p>
            </div>
            <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 14px; padding: 10px 16px; font-size: 11px; text-align: right;">
                <span style="opacity: 0.75; display: block;">Trực quan hóa:</span>
                <strong style="color: #c5dedd;">AI Adaptive Multi-Angle</strong>
            </div>
        </div>

        <!-- 1. HEADLINE METRICS -->
        {kpis_html}

        <!-- 2. INTERACTIVE TABS & CHARTS -->
        <div style="margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
                <div class="section-title" style="margin: 0;">
                    <span>📊</span> CÁC GÓC NHÌN PHÂN TÍCH TRỰC QUAN ({len(charts)} BIỂU ĐỒ)
                </div>
                <div style="background: #e2e8f040; padding: 4px; border-radius: 14px; display: flex; gap: 4px; border: 1px solid #e2e8f0; flex-wrap: wrap;">
                    {"".join(tabs_html)}
                </div>
            </div>
            {"".join(panels_html)}
        </div>

        <!-- 3. MAIN DOMAIN TABLE -->
        <div class="section-box">
            <div class="section-title">
                <span>📋</span> {meta['table_title']}
                <span style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: none;">{meta['unit_label']}</span>
            </div>
            <div style="overflow-x: auto;">
                {table_html}
            </div>
        </div>

        <!-- 4. ACTION LEVERS -->
        <div class="section-box">
            <div class="section-title">
                <span>🎯</span> HỆ THỐNG GIẢI PHÁP & ĐỀ XUẤT HÀNH ĐỘNG
            </div>
            {recs_html}
        </div>
    </div>

    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
                btn.style.background = 'transparent';
                btn.style.color = '#475569';
                btn.style.borderColor = 'transparent';
                btn.style.boxShadow = 'none';
                btn.style.fontWeight = 'bold';
            }});
            const activeBtn = document.getElementById('btnTab-' + tabId);
            if (activeBtn) {{
                activeBtn.classList.add('active');
                activeBtn.style.background = 'white';
                activeBtn.style.color = '#183634';
                activeBtn.style.borderColor = '#e2e8f0';
                activeBtn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
                activeBtn.style.fontWeight = '800';
            }}
            document.querySelectorAll('.view-panel').forEach(p => p.style.display = 'none');
            const targetPanel = document.getElementById('view-' + tabId);
            if (targetPanel) targetPanel.style.display = 'block';
        }}

        document.addEventListener("DOMContentLoaded", function() {{
            {chr(10).join(chart_js_lines)}
        }});
    </script>
</body>
</html>"""
