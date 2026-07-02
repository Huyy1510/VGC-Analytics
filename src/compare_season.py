import json
import os
import re
import sys
import argparse
import datetime

# Get project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def parse_args():
    parser = argparse.ArgumentParser(description="So sánh xu hướng metagame cả mùa giải từ nhiều tệp JSON báo cáo.")
    parser.add_argument("files", nargs="+", help="Danh sách các file JSON báo cáo giải đấu (cách nhau bởi dấu cách)")
    parser.add_argument("-n", "--name", default="VGC Season", help="Tên của mùa giải (ví dụ: Summer Season 2026)")
    parser.add_argument("-o", "--output-dir", help="Thư mục lưu báo cáo kết quả (mặc định: results/season/)")
    return parser.parse_args()

def parse_date(date_str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.datetime.min

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file JSON {filepath}: {e}", file=sys.stderr)
        return None

def main():
    args = parse_args()
    
    output_dir = args.output_dir if args.output_dir else os.path.join(PROJECT_ROOT, "results", "season")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Đọc tất cả các tệp JSON và lọc tệp hợp lệ
    tournaments = []
    for filepath in args.files:
        data = load_json(filepath)
        if not data:
            continue
        
        # Kiểm tra cấu trúc tối thiểu
        if "tournament_name" not in data or "pokemon_usage" not in data:
            print(f"Bỏ qua file không hợp lệ: {filepath}", file=sys.stderr)
            continue
            
        tournaments.append({
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "name": data.get("tournament_name", "Tournament"),
            "date_str": data.get("date", "N/A"),
            "date": parse_date(data.get("date", "")),
            "format": data.get("format", "VGC"),
            "total_players": data.get("total_players", 0),
            "teams_analyzed": data.get("teams_analyzed", 0),
            "pokemon_usage": data.get("pokemon_usage", [])
        })
        
    if not tournaments:
        print("Lỗi: Không tìm thấy tệp dữ liệu giải đấu hợp lệ để tiến hành so sánh.", file=sys.stderr)
        sys.exit(1)
        
    # Sắp xếp các giải đấu theo trình tự thời gian tăng dần (cũ đến mới)
    tournaments.sort(key=lambda x: x["date"])
    
    print(f"Đang phân tích mùa giải: {args.name}")
    print(f"Tìm thấy {len(tournaments)} giải đấu tham gia:")
    for idx, t in enumerate(tournaments):
        print(f"  [{idx+1}] {t['name']} ({t['date_str']}) - Format: {t['format']}")
        
    # 2. Thu thập và tính toán tỉ lệ sử dụng của từng Pokemon qua các giải đấu
    pokemon_series = {}
    pokemon_counts = {}  # Tổng số lần sử dụng qua mùa giải để tính trung bình
    
    num_tours = len(tournaments)
    
    # Gom danh sách tất cả Pokémon xuất hiện trong mùa giải
    all_poke_names = set()
    for t in tournaments:
        for p in t["pokemon_usage"]:
            all_poke_names.add(p["name"])
            
    # Khởi tạo chuỗi thời gian cho mỗi Pokémon với giá trị mặc định 0.0%
    for name in all_poke_names:
        pokemon_series[name] = [0.0] * num_tours
        pokemon_counts[name] = [0] * num_tours
        
    # Điền dữ liệu thực tế vào chuỗi thời gian
    for t_idx, t in enumerate(tournaments):
        for p in t["pokemon_usage"]:
            name = p["name"]
            pokemon_series[name][t_idx] = p.get("percentage", 0.0)
            pokemon_counts[name][t_idx] = p.get("count", 0)
            
    # Tính trung bình tỉ lệ sử dụng qua tất cả các giải đấu để chọn ra Top Pokémon của mùa giải
    pokemon_avg_usage = {}
    for name in all_poke_names:
        pokemon_avg_usage[name] = sum(pokemon_series[name]) / num_tours
        
    # Sắp xếp Pokémon theo tỉ lệ sử dụng trung bình giảm dần
    sorted_pokes = sorted(pokemon_avg_usage.items(), key=lambda x: x[1], reverse=True)
    
    # 3. Phân tích thống kê Item của từng Pokemon qua cả mùa giải
    pokemon_items = {}
    for name in all_poke_names:
        items_agg = {}
        total_poke_appearances = 0
        
        for t in tournaments:
            p_data = next((p for p in t["pokemon_usage"] if p["name"] == name), None)
            if p_data:
                tour_count = p_data.get("count", 0)
                total_poke_appearances += tour_count
                
                for itm in p_data.get("items", []):
                    itm_name = itm["name"]
                    itm_cnt = itm.get("count", 0)
                    items_agg[itm_name] = items_agg.get(itm_name, 0) + itm_cnt
                    
        sorted_items = []
        if total_poke_appearances > 0:
            for itm_name, cnt in items_agg.items():
                pct = (cnt / total_poke_appearances) * 100
                sorted_items.append({
                    "name": itm_name,
                    "count": cnt,
                    "percentage": pct
                })
            sorted_items.sort(key=lambda x: x["count"], reverse=True)
            
        pokemon_items[name] = sorted_items[:5] # Lấy Top 5 items phổ biến nhất
        
    # 4. Phân tích Dịch chuyển Format (Format Transition Analysis)
    formats = []
    for t in tournaments:
        if t["format"] not in formats:
            formats.append(t["format"])
            
    format_shift_data = {}
    has_format_shift = len(formats) > 1
    
    if has_format_shift:
        print(f"Phát hiện sự thay đổi thể thức trong mùa giải: {' -> '.join(formats)}")
        format_indices = {fmt: [] for fmt in formats}
        for idx, t in enumerate(tournaments):
            format_indices[t["format"]].append(idx)
            
        fmt_a = formats[0]
        fmt_b = formats[-1]
        
        indices_a = format_indices[fmt_a]
        indices_b = format_indices[fmt_b]
        
        shift_results = []
        for name in all_poke_names:
            series = pokemon_series[name]
            avg_a = sum(series[i] for i in indices_a) / len(indices_a)
            avg_b = sum(series[i] for i in indices_b) / len(indices_b)
            diff = avg_b - avg_a
            
            shift_results.append({
                "name": name,
                "avg_a": avg_a,
                "avg_b": avg_b,
                "diff": diff
            })
            
        # Tìm Winners (tăng mạnh nhất) và Losers (giảm mạnh nhất)
        winners = sorted([r for r in shift_results if r["diff"] > 0], key=lambda x: x["diff"], reverse=True)[:5]
        losers = sorted([r for r in shift_results if r["diff"] < 0], key=lambda x: x["diff"])[:5]
        
        format_shift_data = {
            "format_a": fmt_a,
            "format_b": fmt_b,
            "winners": winners,
            "losers": losers
        }
        
    # 5. Chuẩn bị dữ liệu cho file JSON kết quả
    top_pokes_for_chart = [p[0] for p in sorted_pokes[:10]] # Top 10 vẽ chart
    
    chart_datasets = []
    for name in top_pokes_for_chart:
        chart_datasets.append({
            "name": name,
            "data": pokemon_series[name]
        })
        
    season_json_data = {
        "season_name": args.name,
        "generated_date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "formats_present": formats,
        "has_format_shift": has_format_shift,
        "tournaments": [
            {
                "name": t["name"],
                "date": t["date_str"],
                "format": t["format"],
                "total_players": t["total_players"]
            } for t in tournaments
        ],
        "top_pokemon_trends": chart_datasets,
        "all_pokemon_matrix": [
            {
                "name": name,
                "avg_percentage": avg,
                "items": pokemon_items.get(name, []),
                "history": [
                    {"tour_name": tournaments[i]["name"], "percentage": pokemon_series[name][i], "count": pokemon_counts[name][i]}
                    for i in range(num_tours)
                ]
            } for name, avg in sorted_pokes
        ],
        "format_shift": format_shift_data
    }
    
    # Lưu file JSON dữ liệu
    safe_season_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', args.name.replace(" ", "_"))
    json_output_path = os.path.join(output_dir, f"{safe_season_name}_season.json")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(season_json_data, f, ensure_ascii=False, indent=4)
        
    # 6. Tạo file HTML Báo cáo
    html_output_path = os.path.join(output_dir, f"{safe_season_name}_season.html")
    
    chart_labels = [f"{t['name']} ({t['date_str']})" for t in tournaments]
    
    format_segments = []
    for idx, t in enumerate(tournaments):
        format_segments.append(t["format"])
        
    # Tạo mã HTML
    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metagame Season Trend: {args.name}</title>
    <!-- Google Fonts: Outfit -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {{
            --bg-dark: #090d16;
            --bg-main: #0e1424;
            --bg-card: #151d30;
            --border: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent: #10b981;
            --accent-glow: rgba(16, 185, 129, 0.15);
            --danger: #ef4444;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }}

        body {{
            background-color: var(--bg-dark);
            color: var(--text-main);
            padding: 2rem;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            margin-bottom: 2.5rem;
            text-align: center;
        }}

        .header-title {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .header-meta {{
            font-size: 1rem;
            color: var(--text-muted);
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            margin-top: 0.75rem;
            flex-wrap: wrap;
        }}

        .meta-badge {{
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            padding: 0.35rem 0.85rem;
            border-radius: 8px;
            font-size: 0.85rem;
        }}

        /* Tabs Navigation */
        .tabs {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
        }}

        .tab-button {{
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1rem;
            font-weight: 600;
            padding: 0.6rem 1.25rem;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s ease;
        }}

        .tab-button:hover {{
            color: #fff;
            background-color: rgba(255, 255, 255, 0.02);
        }}

        .tab-button.active {{
            color: var(--primary);
            background-color: var(--primary-glow);
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .card {{
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 2rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            margin-bottom: 2rem;
        }}

        .card-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 1.25rem;
        }}

        /* Table design */
        .table-container {{
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid var(--border);
            background-color: var(--bg-main);
        }}

        .matrix-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            text-align: left;
        }}

        .matrix-table th, .matrix-table td {{
            padding: 1rem 1.25rem;
            border: 1px solid var(--border);
            vertical-align: middle;
        }}

        .matrix-table thead th {{
            background-color: rgba(255, 255, 255, 0.02);
            font-weight: 600;
            color: var(--text-muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .matrix-table td.heatmap-cell {{
            text-align: center;
            font-weight: 700;
            color: #fff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }}

        .pokemon-sprite-mini {{
            width: 32px;
            height: 32px;
            object-fit: contain;
            vertical-align: middle;
        }}

        .poke-info-cell {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
        }}

        /* Expandable row and progress bar chart styles */
        .expandable-row {{
            cursor: pointer;
            transition: background-color 0.2s ease;
        }}

        .expandable-row:hover {{
            background-color: rgba(255, 255, 255, 0.025) !important;
        }}

        .detail-row {{
            display: none;
            background-color: rgba(7, 10, 19, 0.4);
        }}

        .detail-row.open {{
            display: table-row;
        }}

        .detail-container {{
            padding: 1.25rem 2rem;
            border-left: 4px solid var(--primary);
            text-align: left;
        }}

        .item-chart-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .item-bars-list {{
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            max-width: 600px;
            padding: 0.25rem 0;
        }}

        .item-bar-wrapper {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .item-bar-label {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            min-width: 180px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-main);
        }}

        .item-sprite-mini {{
            width: 20px;
            height: 20px;
            object-fit: contain;
        }}

        .item-bar-outer {{
            flex-grow: 1;
            height: 8px;
            background-color: rgba(255, 255, 255, 0.03);
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .item-bar-inner {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary), #a78bfa);
            border-radius: 4px;
            box-shadow: 0 0 8px rgba(99, 102, 241, 0.4);
        }}

        .item-bar-val {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent);
            min-width: 50px;
            text-align: right;
        }}

        /* Shift Analysis Styles */
        .shift-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}

        @media (max-width: 768px) {{
            .shift-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .shift-card {{
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .shift-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .shift-item:last-child {{
            border-bottom: none;
        }}

        .shift-label {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
        }}

        .shift-val-win {{
            color: var(--accent);
            font-weight: 700;
        }}

        .shift-val-loss {{
            color: var(--danger);
            font-weight: 700;
        }}

        .shift-meta-p {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>

    <div class="container">
        
        <!-- Header -->
        <div class="header">
            <h1 class="header-title">📊 Metagame Season Analysis</h1>
            <div style="font-size: 1.5rem; font-weight: 600; color: var(--primary); margin-top: 0.25rem;">{args.name}</div>
            
            <div class="header-meta">
                <span class="meta-badge">📅 Generated: {season_json_data['generated_date']}</span>
                <span class="meta-badge">🏆 Tournaments: {num_tours}</span>
                <span class="meta-badge">📋 Formats: {", ".join(formats)}</span>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('chart')">📈 Trend Charts</button>
            <button class="tab-button" onclick="switchTab('matrix')">🔲 Heatmap Matrix</button>
            {"<button class='tab-button' onclick=\"switchTab('shift')\">🔄 Format Shifts</button>" if has_format_shift else ""}
        </div>

        <!-- Tab: Line Chart -->
        <div id="tab-chart" class="tab-content active">
            <div class="card">
                <h3 class="card-title">Top 10 Pokémon Usage Trend Timeline</h3>
                <div style="position: relative; height: 500px; width: 100%;">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Tab: Heatmap Matrix Table -->
        <div id="tab-matrix" class="tab-content">
            <div class="card">
                <h3 class="card-title">Detailed Usage Matrix (%) <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal; margin-left: 0.5rem;">(Click vào mỗi dòng để xem Item sử dụng phổ biến)</span></h3>
                <div class="table-container">
                    <table class="matrix-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Pokémon</th>
                                <th>Avg. Usage</th>
                                { "".join(f"<th>{t['name']}</th>" for t in tournaments) }
                            </tr>
                        </thead>
                        <tbody>
        """
        
    for idx, (name, avg_pct) in enumerate(sorted_pokes):
        if idx >= 40:
            break
            
        name_slug = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        
        html_content += f"""
                            <tr class="expandable-row" onclick="toggleRow('details-{name_slug}')">
                                <td style="text-align: center; color: var(--text-muted); font-weight: 700;">#{idx+1}</td>
                                <td>
                                    <div class="poke-info-cell">
                                        <img src="https://storage.longngphuc.id.vn/public/sprites/pokemon/{name.lower().replace(" ", "-").replace("-mega-x", "-megax").replace("-mega-y", "-megay").replace("kommo-o", "kommoo").replace("mimikyu-disguised", "mimikyu").replace("aegislash-shield", "aegislash")}.png" class="pokemon-sprite-mini" onerror="this.src='https://storage.longngphuc.id.vn/public/sprites/pokemon/substitute.png'">
                                        <span>{name}</span>
                                    </div>
                                </td>
                                <td style="font-weight: 700; color: var(--primary);">{avg_pct:.1f}%</td>
        """
        
        for val in pokemon_series[name]:
            # Heatmap color scale logic: nổi bật và trực quan
            if val == 0:
                bg_color = "#0f1524"
                border_color = "var(--border)"
            elif val < 10:
                bg_color = "rgba(99, 102, 241, 0.15)"      # Indigo nhạt
                border_color = "rgba(99, 102, 241, 0.2)"
            elif val < 25:
                bg_color = "rgba(236, 72, 153, 0.55)"     # Pink nổi bật
                border_color = "rgba(236, 72, 153, 0.6)"
            elif val < 40:
                bg_color = "rgba(139, 92, 246, 0.35)"     # Violet sáng hơn
                border_color = "rgba(139, 92, 246, 0.4)"
            else:
                bg_color = "rgba(16, 185, 129, 0.65)"     # Emerald rực rỡ
                border_color = "rgba(16, 185, 129, 0.7)"
                
            html_content += f"""
                                <td class="heatmap-cell" style="background-color: {bg_color}; border: 1px solid {border_color};">
                                    {val:.1f}%
                                </td>
            """
            
        # Tạo HTML Bar Chart cho Item
        items_html = ""
        if pokemon_items.get(name):
            items_html = '<div class="item-bars-list">'
            for itm in pokemon_items[name]:
                itm_name = itm["name"]
                itm_pct = itm["percentage"]
                item_slug = itm_name.lower().strip().replace(" ", "-").replace("[", "").replace("]", "")
                item_sprite = f"https://storage.longngphuc.id.vn/public/sprites/items/{item_slug}.png"
                
                items_html += f"""
                    <div class="item-bar-wrapper">
                        <div class="item-bar-label">
                            <img src="{item_sprite}" class="item-sprite-mini" onerror="this.style.display='none'">
                            <span>{itm_name}</span>
                        </div>
                        <div class="item-bar-outer">
                            <div class="item-bar-inner" style="width: {itm_pct:.1f}%"></div>
                        </div>
                        <div class="item-bar-val">{itm_pct:.1f}%</div>
                    </div>
                """
            items_html += '</div>'
        else:
            items_html = '<div class="empty-state-cell" style="font-style: italic; color: var(--text-muted);">N/A (Chưa mang Item)</div>'
            
        colspan_val = 3 + num_tours
        
        html_content += f"""
                            </tr>
                            <tr id="details-{name_slug}" class="detail-row">
                                <td colspan="{colspan_val}">
                                    <div class="detail-container">
                                        <h4 class="item-chart-title">
                                            <span>🎒</span> Popular Items for {name} this Season
                                        </h4>
                                        {items_html}
                                    </div>
                                </td>
                            </tr>
        """
        
    html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    """
    
    if has_format_shift:
        fmt_a = format_shift_data["format_a"]
        fmt_b = format_shift_data["format_b"]
        
        html_content += f"""
        <div id="tab-shift" class="tab-content">
            <div class="card">
                <h3 class="card-title">Rule Change Impact Analysis ({fmt_a} ➔ {fmt_b})</h3>
                <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 2rem;">
                    So sánh tỉ lệ sử dụng trung bình của Pokémon ở giai đoạn đầu ({fmt_a}) và giai đoạn đổi luật ({fmt_b}) để xác định những biến đổi meta lớn nhất.
                </p>
                
                <div class="shift-grid">
                    <!-- Winners -->
                    <div class="shift-card" style="border-color: rgba(16, 185, 129, 0.2);">
                        <h4 class="card-title" style="color: var(--accent); display: flex; align-items: center; gap: 0.5rem;">
                            📈 Metagame Winners (Tăng mạnh nhất)
                        </h4>
        """
        
        for w in format_shift_data["winners"]:
            name = w["name"]
            html_content += f"""
                        <div class="shift-item">
                            <div class="shift-label">
                                <img src="https://storage.longngphuc.id.vn/public/sprites/pokemon/{name.lower().replace(" ", "-").replace("-mega-x", "-megax").replace("-mega-y", "-megay").replace("kommo-o", "kommoo").replace("mimikyu-disguised", "mimikyu").replace("aegislash-shield", "aegislash")}.png" class="pokemon-sprite-mini" onerror="this.src='https://storage.longngphuc.id.vn/public/sprites/pokemon/substitute.png'">
                                <span>{name}</span>
                            </div>
                            <div style="text-align: right;">
                                <div class="shift-val-win">+{w['diff']:.1f}%</div>
                                <div class="shift-meta-p">{w['avg_a']:.1f}% ➔ {w['avg_b']:.1f}%</div>
                            </div>
                        </div>
            """
            
        html_content += f"""
                    </div>
                    
                    <!-- Losers -->
                    <div class="shift-card" style="border-color: rgba(239, 68, 68, 0.2);">
                        <h4 class="card-title" style="color: var(--danger); display: flex; align-items: center; gap: 0.5rem;">
                            📉 Metagame Losers (Sụt giảm nhiều nhất)
                        </h4>
        """
        
        for l in format_shift_data["losers"]:
            name = l["name"]
            html_content += f"""
                        <div class="shift-item">
                            <div class="shift-label">
                                <img src="https://storage.longngphuc.id.vn/public/sprites/pokemon/{name.lower().replace(" ", "-").replace("-mega-x", "-megax").replace("-mega-y", "-megay").replace("kommo-o", "kommoo").replace("mimikyu-disguised", "mimikyu").replace("aegislash-shield", "aegislash")}.png" class="pokemon-sprite-mini" onerror="this.src='https://storage.longngphuc.id.vn/public/sprites/pokemon/substitute.png'">
                                <span>{name}</span>
                            </div>
                            <div style="text-align: right;">
                                <div class="shift-val-loss">{l['diff']:.1f}%</div>
                                <div class="shift-meta-p">{l['avg_a']:.1f}% ➔ {l['avg_b']:.1f}%</div>
                            </div>
                        </div>
            """
            
        html_content += """
                    </div>
                </div>
            </div>
        </div>
        """
        
    chart_datasets_js = []
    colors_palette = [
        "#818cf8", "#34d399", "#f472b6", "#fbbf24", "#60a5fa", 
        "#a78bfa", "#f87171", "#2dd4bf", "#fb7185", "#fb923c"
    ]
    
    for idx, ds in enumerate(chart_datasets):
        color = colors_palette[idx % len(colors_palette)]
        chart_datasets_js.append({
            "label": ds["name"],
            "data": ds["data"],
            "borderColor": color,
            "backgroundColor": color + "1a",
            "tension": 0.25,
            "borderWidth": 3,
            "pointRadius": 4,
            "pointHoverRadius": 7
        })
        
    html_content += f"""
    </div> <!-- container -->

    <script>
        // Toggle row detail for item chart
        function toggleRow(id) {{
            const row = document.getElementById(id);
            if (row) {{
                row.classList.toggle('open');
            }}
        }}

        // Tab switching logic
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            const btn = Array.from(document.querySelectorAll('.tab-button')).find(b => b.getAttribute('onclick').includes(tabId));
            if (btn) btn.classList.add('active');
            
            const content = document.getElementById('tab-' + tabId);
            if (content) content.classList.add('active');
        }}

        // Chart.js render timeline
        const ctx = document.getElementById('trendChart').getContext('2d');
        const formatSegments = {json.dumps(format_segments)};
        
        const formatShiftPlugin = {{
            id: 'formatShiftLine',
            beforeDraw: (chart) => {{
                const {{ ctx, chartArea: {{ top, bottom }}, scales: {{ x }} }} = chart;
                ctx.save();
                
                for (let i = 1; i < formatSegments.length; i++) {{
                    if (formatSegments[i] !== formatSegments[i-1]) {{
                        const x1 = x.getPixelForValue(i - 1);
                        const x2 = x.getPixelForValue(i);
                        const xPos = (x1 + x2) / 2;
                        
                        ctx.strokeStyle = 'rgba(245, 158, 11, 0.6)';
                        ctx.lineWidth = 2;
                        ctx.setLineDash([6, 6]);
                        ctx.beginPath();
                        ctx.moveTo(xPos, top);
                        ctx.lineTo(xPos, bottom);
                        ctx.stroke();
                        
                        ctx.fillStyle = '#f59e0b';
                        ctx.font = 'bold 11px Outfit';
                        ctx.textAlign = 'center';
                        ctx.fillText('SHIFT TO ' + formatSegments[i], xPos, top + 20);
                    }}
                }}
                ctx.restore();
            }}
        }};

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_labels, ensure_ascii=False)},
                datasets: {json.dumps(chart_datasets_js, ensure_ascii=False)}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            color: '#e5e7eb',
                            font: {{ family: 'Outfit', size: 12 }},
                            padding: 15
                        }}
                    }},
                    tooltip: {{
                        padding: 12,
                        titleFont: {{ family: 'Outfit', size: 13, weight: 'bold' }},
                        bodyFont: {{ family: 'Outfit', size: 12 }},
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                        ticks: {{
                            color: '#9ca3af',
                            font: {{ family: 'Outfit' }}
                        }}
                    }},
                    y: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                        ticks: {{
                            color: '#9ca3af',
                            font: {{ family: 'Outfit' }},
                            callback: function(value) {{ return value + '%'; }}
                        }},
                        min: 0
                    }}
                }}
            }},
            plugins: [formatShiftPlugin]
        }});
    </script>
</body>
</html>
"""
    
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\n==================================================")
    print(f" THÀNH CÔNG: Đã tạo và lưu báo cáo mùa giải tại:")
    print(f" -> JSON: {os.path.abspath(json_output_path)}")
    print(f" -> HTML: {os.path.abspath(html_output_path)}")
    print(f"==================================================\n")

if __name__ == "__main__":
    main()
