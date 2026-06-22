#!/usr/bin/env python3
import urllib.request
import urllib.error
import urllib.parse
import json
import ssl
import re
import os
import sys
import argparse
from collections import Counter

# Khởi tạo SSL context không xác thực chứng chỉ (để tránh lỗi SSL trên macOS)
ssl_context = ssl._create_unverified_context()

# Đường dẫn đến các file ánh xạ tên
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
POKEMON_MAP_PATH = os.path.join(project_root, "data", "pokemon_name_mapping.json")
ITEM_MAP_PATH = os.path.join(project_root, "data", "item_name_mapping.json")

# Tải từ điển ánh xạ nếu có
pokemon_map = {}
item_map = {}

if os.path.exists(POKEMON_MAP_PATH):
    try:
        with open(POKEMON_MAP_PATH, "r", encoding="utf-8") as f:
            pokemon_map = json.load(f)
    except Exception as e:
        print(f"Không thể đọc file ánh xạ Pokemon: {e}", file=sys.stderr)

if os.path.exists(ITEM_MAP_PATH):
    try:
        with open(ITEM_MAP_PATH, "r", encoding="utf-8") as f:
            item_map = json.load(f)
    except Exception as e:
        print(f"Không thể đọc file ánh xạ vật phẩm: {e}", file=sys.stderr)


def extract_tournament_id(input_str, api_key=None):
    """
    Trích xuất ID giải đấu (24 ký tự hex) từ chuỗi nhập vào hoặc URL.
    Nếu là URL không chứa ID hex trực tiếp (dạng slug), tải trang để tìm ID.
    """
    input_str = input_str.strip()
    
    # 1. Tìm chuỗi hex 24 ký tự trực tiếp
    hex_match = re.search(r'[0-9a-f]{24}', input_str)
    if hex_match:
        return hex_match.group(0)
    
    # 2. Nếu là URL nhưng không chứa hex trực tiếp (ví dụ URL có slug)
    if input_str.startswith("http://") or input_str.startswith("https://"):
        print("Đang quét trang HTML để tìm ID giải đấu...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            if api_key:
                headers['X-Access-Key'] = api_key
            
            # Để an toàn cho private tournament, thêm cả API key vào query param nếu có
            url = input_str
            if api_key:
                if "?" in url:
                    url = f"{url}&key={api_key}"
                else:
                    url = f"{url}?key={api_key}"
                    
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context) as response:
                html = response.read().decode('utf-8')
            
            # Tìm tất cả chuỗi hex 24 ký tự trong HTML
            hex_ids = re.findall(r'[0-9a-f]{24}', html)
            if hex_ids:
                resolved_id = hex_ids[0]
                print(f"Tìm thấy ID giải đấu từ URL: {resolved_id}")
                return resolved_id
        except Exception as e:
            print(f"Lỗi khi tải trang để tìm ID giải đấu: {e}", file=sys.stderr)
            
    return None


def get_api_data(url, api_key=None):
    """Gửi yêu cầu GET đến API Limitless, có hỗ trợ API key cho giải đấu riêng tư (private)"""
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }
    if api_key:
        headers['X-Access-Key'] = api_key
        # Để an toàn nhất, gắn thêm key vào query parameters của URL luôn
        if "?" in url:
            url = f"{url}&key={api_key}"
        else:
            url = f"{url}?key={api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in [401, 403, 404]:
            print(f"\n[LỖI] Không thể truy cập API (HTTP {e.code}).", file=sys.stderr)
            print("Giải đấu này có thể là GIẢI ĐẤU RIÊNG TƯ (PRIVATE) hoặc ID không hợp lệ.", file=sys.stderr)
            print("Nếu là giải riêng tư, bạn cần cung cấp API Key hợp lệ bằng tham số `-k` / `--key` hoặc thiết lập biến môi trường `LIMITLESS_API_KEY`.\n", file=sys.stderr)
        raise e


def map_pokemon_name(name):
    """Ánh xạ tên Pokemon theo từ điển hoặc định dạng chuẩn của joaoabel"""
    if not name:
        return ""
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Quy tắc chung cho các dạng vùng miền (Regional forms)
    if name_lower.startswith("hisuian "):
        return name_clean[8:] + "-Hisui"
    if name_lower.startswith("alolan "):
        return name_clean[7:] + "-Alola"
    if name_lower.startswith("galarian "):
        return name_clean[9:] + "-Galar"
    if name_lower.startswith("paldean "):
        return name_clean[8:] + "-Paldea"
        
    # Chuẩn hóa chuỗi trước khi tra cứu
    name_normalized = name_lower.replace(" (", "-").replace(")", "").replace(" - ", "-").replace(" ", "-")
    
    # Hỗ trợ dạng "Wash Rotom" / "Rotom Wash"
    if "rotom" in name_lower:
        if "wash" in name_lower:
            return "Rotom-wash"
        if "heat" in name_lower:
            return "Rotom-heat"
        if "mow" in name_lower:
            return "Rotom-mow"
        if "frost" in name_lower:
            return "Rotom-frost"
        if "fan" in name_lower:
            return "Rotom-fan"
            
    # Hỗ trợ Floette Eternal và Floette Eternal Mega
    if "eternal" in name_lower and "floette" in name_lower:
        if "mega" in name_lower:
            return "floette-eternal-mega"
        return "Floette-eternal"
        
    name_normalized = name_normalized.replace("-female", "-f").replace("-male", "-m")
    
    # Ánh xạ thủ công cho các dạng viết khác của Limitless
    manual_maps = {
        "wash-rotom": "Rotom-wash",
        "heat-rotom": "Rotom-heat",
        "mow-rotom": "Rotom-mow",
        "frost-rotom": "Rotom-frost",
        "fan-rotom": "Rotom-fan",
        "eternal-flower-floette": "Floette-eternal",
        "floette-eternal-flower": "Floette-eternal",
        "indeedee-female": "Indeedee-f",
        "indeedee-f": "Indeedee-f",
        "indeedee-m": "Indeedee-m",
        "basculegion-female": "Basculegion-f",
        "basculegion-f": "Basculegion-f",
        "basculegion-m": "Basculegion-m",
        "ogerpon-cornerstone-mask": "Ogerpon-cornerstone",
        "ogerpon-cornerstone": "Ogerpon-cornerstone",
        "ogerpon-wellspring-mask": "Ogerpon-wellspring",
        "ogerpon-wellspring": "Ogerpon-wellspring",
        "ogerpon-hearthflame-mask": "Ogerpon-hearthflame",
        "ogerpon-hearthflame": "Ogerpon-hearthflame",
        "urshifu-rapid-strike-style": "Urshifu-rapid-strike",
        "urshifu-rapid-strike": "Urshifu-rapid-strike",
        "urshifu-rs": "Urshifu-rapid-strike",
        "urshifu-single-strike-style": "Urshifu-single-strike",
        "urshifu-single-strike": "Urshifu-single-strike",
        "urshifu-ss": "Urshifu-single-strike",
        "calyrex-ice-rider": "Calyrex-ice",
        "calyrex-ice": "Calyrex-ice",
        "calyrex-shadow-rider": "Calyrex-shadow",
        "calyrex-shadow": "Calyrex-shadow",
        "eternal-flower-floette-mega": "floette-eternal-mega",
        "floette-eternal-mega": "floette-eternal-mega",
    }
    
    if name_normalized in manual_maps:
        return manual_maps[name_normalized]
        
    # Tra cứu trong từ điển pokemon_name_mapping.json
    if name_lower in pokemon_map:
        return pokemon_map[name_lower]
    if name_normalized in pokemon_map:
        return pokemon_map[name_normalized]
        
    return name_clean


def map_item_name(name):
    """Ánh xạ tên vật phẩm theo từ điển của joaoabel"""
    if not name:
        return ""
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Chuẩn hóa nếu không có vật phẩm
    if name_lower in ["no item", "none", "no_item"]:
        return ""
        
    if name_lower in item_map:
        return item_map[name_lower]
        
    return name_clean


def sort_counter(counter):
    """Sắp xếp một Counter trả về danh sách tuple (item, count) theo thứ tự giảm dần"""
    return sorted(counter.items(), key=lambda x: x[1], reverse=True)


def write_html_report(data, filename):
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Usage Statistics Report - {data['tournament_name']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #151d30;
            --bg-active: #1e293b;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border: #1e293b;
            --success: #10b981;
            --danger: #ef4444;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 2rem;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, var(--bg-card) 0%, #1e1b4b 100%);
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 2rem;
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}
        
        .header-title {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            background: linear-gradient(to right, #ffffff, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header-meta {{
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            font-size: 0.95rem;
            color: var(--text-muted);
        }}
        
        .meta-badge {{
            background-color: rgba(255, 255, 255, 0.05);
            padding: 0.4rem 0.8rem;
            border-radius: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 2rem;
            height: calc(100vh - 240px);
            min-height: 600px;
        }}
        
        @media (max-width: 960px) {{
            body {{
                padding: 1rem;
            }}
            .dashboard {{
                grid-template-columns: 1fr;
                height: auto;
            }}
        }}
        
        .sidebar {{
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        }}
        
        .search-container {{
            padding: 1.25rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .search-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s;
        }}
        
        .search-input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }}
        
        .pokemon-list {{
            flex: 1;
            overflow-y: auto;
            list-style: none;
        }}
        
        /* Custom scrollbar */
        .pokemon-list::-webkit-scrollbar, .details-panel::-webkit-scrollbar {{
            width: 6px;
        }}
        .pokemon-list::-webkit-scrollbar-track, .details-panel::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .pokemon-list::-webkit-scrollbar-thumb, .details-panel::-webkit-scrollbar-thumb {{
            background: #1e293b;
            border-radius: 10px;
        }}
        .pokemon-list::-webkit-scrollbar-thumb:hover, .details-panel::-webkit-scrollbar-thumb:hover {{
            background: #334155;
        }}
        
        .pokemon-item {{
            display: flex;
            align-items: center;
            padding: 1rem 1.25rem;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
            transition: all 0.25s;
        }}
        
        .pokemon-item:hover {{
            background-color: rgba(99, 102, 241, 0.04);
        }}
        
        .pokemon-item.active {{
            background-color: var(--bg-active);
            border-left: 4px solid var(--primary);
            padding-left: calc(1.25rem - 4px);
        }}
        
        .pokemon-rank {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted);
            width: 28px;
        }}
        
        .pokemon-name {{
            font-weight: 500;
            flex: 1;
        }}
        
        .pokemon-pct {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--primary);
            background-color: var(--primary-glow);
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
        }}
        
        .details-panel {{
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 2.5rem;
            overflow-y: auto;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}
        
        .details-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
        }}
        
        .details-title {{
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .details-subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-top: 0.25rem;
        }}
        
        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
        }}
        
        .card {{
            background-color: var(--bg-main);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            border-left: 3px solid var(--primary);
            padding-left: 0.6rem;
            color: #a5b4fc;
        }}
        
        .card-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        
        .card-item {{
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
        }}
        
        .item-info {{
            display: flex;
            justify-content: space-between;
            font-size: 0.95rem;
        }}
        
        .item-name {{
            font-weight: 500;
        }}
        
        .item-pct {{
            font-weight: 600;
            color: var(--text-muted);
        }}
        
        .progress-bar {{
            height: 6px;
            background-color: #1e293b;
            border-radius: 10px;
            overflow: hidden;
            width: 100%;
        }}
        
        .progress-fill {{
            height: 100%;
            background-color: var(--primary);
            border-radius: 10px;
            transition: width 0.5s ease-out;
        }}
        
        .badge-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        
        .badge {{
            background-color: #1e293b;
            color: var(--text-main);
            padding: 0.4rem 0.8rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            border: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }}
        
        .badge-pct {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--primary);
        }}
        
        .empty-state {{
            text-align: center;
            color: var(--text-muted);
            padding: 3rem;
            font-size: 1.1rem;
        }}
        
        .card.wide {{
            grid-column: 1 / -1;
        }}
        
        .moves-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 1rem;
        }}
        
        /* Pokémon & Item Sprites styling */
        .pokemon-sprite-mini {{
            width: 32px;
            height: 32px;
            object-fit: contain;
            flex-shrink: 0;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15));
            transition: transform 0.2s ease;
        }}
        .pokemon-item:hover .pokemon-sprite-mini {{
            transform: scale(1.15);
        }}
        .pokemon-sprite-large {{
            width: 80px;
            height: 80px;
            object-fit: contain;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
            background: rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            padding: 4px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            flex-shrink: 0;
        }}
        .item-sprite-mini {{
            width: 24px;
            height: 24px;
            object-fit: contain;
            flex-shrink: 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="header-title">{data['tournament_name']}</h1>
        <div class="header-meta">
            <span class="meta-badge">📅 Date: {data['date']}</span>
            <span class="meta-badge">👥 Players: {data['total_players']}</span>
            <span class="meta-badge">📊 Teams Analyzed: {data['teams_analyzed']}</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="sidebar">
            <div class="search-container">
                <input type="text" class="search-input" id="search" placeholder="Search Pokémon...">
            </div>
            <ul class="pokemon-list" id="list">
                <!-- Pokémon list will appear here -->
            </ul>
        </div>
        
        <div class="details-panel" id="details">
            <!-- Selected Pokémon details will appear here -->
        </div>
    </div>
    
    <script>
        const data = {json_str};
        const pokes = data.pokemon_usage;
        let activeIndex = 0;
        
        function getPokemonSpriteUrl(pokemonName, formName = "") {{
            let slug = pokemonName.trim().toLowerCase()
                .replace(/\\s+/g, '-')
                .replace(/[^a-z0-9\\-]/g, '');
                
            // Sửa lỗi tên một số Pokemon để khớp với file ảnh lưu trên Cloud Storage
            if (slug.startsWith("mimikyu")) {{
                slug = "mimikyu";
            }} else if (slug.startsWith("aegislash")) {{
                slug = "aegislash";
            }} else if (slug.includes("kommo-o")) {{
                slug = slug.replace("kommo-o", "kommoo");
            }}
                
            if (formName) {{
                let fClean = formName.trim().toLowerCase();
                if (fClean !== "base") {{
                    if (fClean === "mega x" || fClean === "mega-x") {{
                        slug += "-megax";
                    }} else if (fClean === "mega y" || fClean === "mega-y") {{
                        slug += "-megay";
                    }} else {{
                        slug += "-" + fClean.replace(/[^a-z0-9]/g, '');
                    }}
                }}
            }}
            return `https://storage.longngphuc.id.vn/public/sprites/pokemon/${{slug}}.png`;
        }}
        
        function getItemSpriteUrl(itemName) {{
            if (!itemName) return "";
            let slug = itemName.trim().toLowerCase()
                .replace(/\\s+/g, '-')
                .replace(/[^a-z0-9\\-]/g, '');
            return `https://storage.longngphuc.id.vn/public/sprites/items/${{slug}}.png`;
        }}
        
        const listEl = document.getElementById("list");
        const detailsEl = document.getElementById("details");
        const searchInput = document.getElementById("search");
        
        function renderList(filter = "") {{
            listEl.innerHTML = "";
            let filteredPokes = pokes;
            if (filter) {{
                filteredPokes = pokes.filter(p => p.name.toLowerCase().includes(filter.toLowerCase()));
            }}
            
            if (filteredPokes.length === 0) {{
                listEl.innerHTML = '<li class="empty-state">No Pokémon found</li>';
                return;
            }}
            
            filteredPokes.forEach((p, idx) => {{
                // Get original index in pokes array
                const originalIdx = pokes.findIndex(op => op.name === p.name);
                const li = document.createElement("li");
                li.className = "pokemon-item" + (originalIdx === activeIndex ? " active" : "");
                li.innerHTML = `
                    <span class="pokemon-rank">#${{p.rank}}</span>
                    <img src="${{getPokemonSpriteUrl(p.name)}}" class="pokemon-sprite-mini" alt="${{p.name}}">
                    <span class="pokemon-name" style="margin-left: 0.5rem;">${{p.name}}</span>
                    <span class="pokemon-pct">${{p.percentage.toFixed(1)}}%</span>
                `;
                li.onclick = () => {{
                    activeIndex = originalIdx;
                    renderList(filter);
                    renderDetails();
                }};
                listEl.appendChild(li);
            }});
        }}
        
        function renderProgressList(items) {{
            if (!items || items.length === 0) return '<div class="empty-state">N/A</div>';
            return '<div class="card-list">' + 
                items.slice(0, 5).map(item => `
                    <div class="card-item">
                        <div class="item-info">
                            <span class="item-name">${{item.name}}</span>
                            <span class="item-pct">${{item.percentage.toFixed(1)}}% (${{item.count}} times)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${{item.percentage}}%"></div>
                        </div>
                    </div>
                `).join('') + '</div>';
        }}
        
        function renderItemsList(items) {{
            if (!items || items.length === 0) return '<div class="empty-state">N/A</div>';
            return '<div class="card-list">' + 
                items.slice(0, 5).map(item => `
                    <div class="card-item">
                        <div class="item-info" style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <img src="${{getItemSpriteUrl(item.name)}}" class="item-sprite-mini" alt="${{item.name}}" onerror="this.style.display='none'">
                                <span class="item-name">${{item.name}}</span>
                            </div>
                            <span class="item-pct">${{item.percentage.toFixed(1)}}% (${{item.count}} times)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${{item.percentage}}%"></div>
                        </div>
                    </div>
                `).join('') + '</div>';
        }}
        
        function renderFormsList(forms, baseName) {{
            if (!forms || forms.length === 0) return '<div class="empty-state">N/A</div>';
            return '<div class="card-list">' + 
                forms.map(form => `
                    <div class="card-item">
                        <div class="item-info" style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <img src="${{getPokemonSpriteUrl(baseName, form.name)}}" class="pokemon-sprite-mini" alt="${{form.name}}">
                                <span class="item-name">${{form.name}}</span>
                            </div>
                            <span class="item-pct">${{form.percentage.toFixed(1)}}% (${{form.count}} times)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${{form.percentage}}%"></div>
                        </div>
                    </div>
                `).join('') + '</div>';
        }}
        
        function renderBadges(items) {{
            if (!items || items.length === 0) return '<div class="empty-state">N/A</div>';
            return '<div class="badge-container">' + 
                items.slice(0, 6).map(item => `
                    <div class="badge">
                        <span>${{item.name}}</span>
                        <span class="badge-pct">${{item.percentage.toFixed(1)}}%</span>
                    </div>
                `).join('') + '</div>';
        }}
        
        function renderDetails() {{
            const p = pokes[activeIndex];
            if (!p) {{
                detailsEl.innerHTML = '<div class="empty-state">Select a Pokémon from the list to view build details</div>';
                return;
            }}
            
            let formsHtml = "";
            if (p.forms && p.forms.length > 1) {{
                formsHtml = `
                    <div class="card">
                        <h3 class="card-title">Forms & Mega Variants</h3>
                        ${{renderFormsList(p.forms, p.name)}}
                    </div>
                `;
            }}
            
            detailsEl.innerHTML = `
                <div class="details-header" style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 1.5rem;">
                        <img src="${{getPokemonSpriteUrl(p.name)}}" class="pokemon-sprite-large" alt="${{p.name}}">
                        <div>
                            <h2 class="details-title">${{p.name}}</h2>
                            <div class="details-subtitle">Rank #${{p.rank}} | Usage: ${{p.count}} times across teams</div>
                        </div>
                    </div>
                    <div style="text-align: right">
                        <div style="font-size: 2.2rem; font-weight: 700; color: var(--primary);">${{p.percentage.toFixed(1)}}%</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted)">Usage Rate</div>
                    </div>
                </div>
                
                <div class="grid-container">
                    ${{formsHtml}}
                    
                    <div class="card">
                        <h3 class="card-title">Popular Items</h3>
                        ${{renderItemsList(p.items)}}
                    </div>
                    
                    <div class="card">
                        <h3 class="card-title">Popular Abilities</h3>
                        ${{renderProgressList(p.abilities)}}
                    </div>
                    
                    <div class="card">
                        <h3 class="card-title">Popular Natures</h3>
                        ${{renderBadges(p.natures)}}
                    </div>
                    
                    <div class="card wide">
                        <h3 class="card-title">Popular Moves</h3>
                        <div class="card-list">
                            <div class="moves-grid">
                                ${{p.moves.slice(0, 12).map(move => `
                                    <div class="badge">
                                        <span>${{move.name}}</span>
                                        <span class="badge-pct">${{move.percentage.toFixed(1)}}%</span>
                                    </div>
                                `).join('')}}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }}
        
        searchInput.oninput = (e) => {{
            const val = e.target.value;
            renderList(val);
        }};
        
        // Khởi động render ban đầu
        renderList();
        renderDetails();
    </script>
</body>
</html>
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)


def main():
    parser = argparse.ArgumentParser(description="Thu thập và phân tích chỉ số sử dụng (Usage Statistics) của giải đấu Limitless (hỗ trợ cả giải đấu Public và Private).")
    parser.add_argument("tournament", help="URL giải đấu Limitless hoặc ID giải đấu (24 ký tự hex)")
    parser.add_argument("-k", "--key", help="API Key của Limitless (hoặc thiết lập biến môi trường LIMITLESS_API_KEY)")
    parser.add_argument("-o", "--output-dir", help="Thư mục lưu kết quả báo cáo (mặc định: thư mục results/ ở thư mục gốc dự án)")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Số lượng Pokemon hàng đầu hiển thị chi tiết (mặc định: 20, truyền -1 để hiển thị tất cả)")
    
    args = parser.parse_args()
    
    output_dir = args.output_dir if args.output_dir else os.path.join(project_root, "results", "usage")
    
    # Lấy API Key từ đối số hoặc từ biến môi trường
    api_key = args.key or os.environ.get("LIMITLESS_API_KEY")
    
    # 1. Trích xuất ID giải đấu
    tour_id = extract_tournament_id(args.tournament, api_key)
    if not tour_id:
        print("Lỗi: Không tìm thấy ID giải đấu hợp lệ (phải chứa chuỗi hex 24 ký tự hoặc URL hợp lệ).", file=sys.stderr)
        sys.exit(1)
        
    print(f"Đang xử lý giải đấu với ID: {tour_id}...")
    
    # 2. Lấy thông tin chi tiết giải đấu
    try:
        details = get_api_data(f"https://play.limitlesstcg.com/api/tournaments/{tour_id}/details", api_key)
    except Exception as e:
        print(f"Lỗi khi lấy thông tin chi tiết giải đấu: {e}", file=sys.stderr)
        sys.exit(1)
        
    tour_name = details.get("name", "Tournament")
    tour_date_raw = details.get("date", "")
    tour_format = details.get("format", "VGC")
    total_players = details.get("players", 0)
    
    # Định dạng ngày DD/MM/YYYY
    tour_date = "N/A"
    if tour_date_raw:
        try:
            parts = tour_date_raw.split("T")[0].split("-")
            tour_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
            
    print(f"Giải đấu: {tour_name}")
    print(f"Ngày đấu: {tour_date} | Thể thức: {tour_format} | Số người chơi đăng ký: {total_players}")
    
    # 3. Lấy bảng xếp hạng và danh sách đội hình
    print("Đang tải bảng xếp hạng và đội hình...")
    try:
        standings = get_api_data(f"https://play.limitlesstcg.com/api/tournaments/{tour_id}/standings", api_key)
    except Exception as e:
        print(f"Lỗi khi tải bảng xếp hạng: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 4. Phân tích chỉ số sử dụng (Usage Statistics)
    n_teams = 0
    pokemon_counts = Counter()
    
    # Cấu trúc dữ liệu chi tiết cho từng Pokemon
    # poke_details[pokemon_name] = { 'items': Counter(), 'abilities': Counter(), 'moves': Counter(), 'teras': Counter(), 'natures': Counter() }
    poke_details = {}
    
    for p in standings:
        decklist = p.get("decklist")
        if not decklist:
            continue
            
        n_teams += 1
        # Theo dõi các pokemon đã xuất hiện trong team này (để tránh đếm trùng nếu có lỗi lặp pokemon trong API)
        seen_in_team = set()
        
        for pm in decklist:
            raw_poke_name = pm.get("name")
            if not raw_poke_name:
                continue
                
            raw_item_name = pm.get("item", "")
            is_mega = False
            item_clean = raw_item_name.strip().lower() if raw_item_name else ""
            if item_clean and item_clean != "eviolite" and (item_clean.endswith("ite") or "ite x" in item_clean or "ite y" in item_clean or "ite-x" in item_clean or "ite-y" in item_clean or "unite x" in item_clean or "unite y" in item_clean or "unite-x" in item_clean or "unite-y" in item_clean):
                is_mega = True
                
            form_name = "Base"
            if is_mega:
                if " x" in item_clean or "-x" in item_clean:
                    form_name = "Mega X"
                elif " y" in item_clean or "-y" in item_clean:
                    form_name = "Mega Y"
                else:
                    form_name = "Mega"
            
            poke_name = map_pokemon_name(raw_poke_name)
                
            if not poke_name or poke_name in seen_in_team:
                continue
                
            seen_in_team.add(poke_name)
            pokemon_counts[poke_name] += 1
            
            if poke_name not in poke_details:
                poke_details[poke_name] = {
                    "items": Counter(),
                    "abilities": Counter(),
                    "moves": Counter(),
                    "teras": Counter(),
                    "natures": Counter(),
                    "forms": Counter()
                }
                
            poke_details[poke_name]["forms"][form_name] += 1
                
            # Thống kê Vật phẩm (Item)
            raw_item = pm.get("item")
            item = map_item_name(raw_item)
            if item:
                poke_details[poke_name]["items"][item] += 1
            elif raw_item and raw_item.lower() not in ["none", "no item", "no_item"]:
                poke_details[poke_name]["items"][raw_item.strip()] += 1
                
            # Thống kê Khả năng (Ability)
            ability = pm.get("ability")
            if ability and ability.strip() and ability.lower() != "none":
                poke_details[poke_name]["abilities"][ability.strip()] += 1
                
            # Thống kê Tera Type
            tera = pm.get("tera")
            if tera and tera.strip() and tera.lower() != "none":
                poke_details[poke_name]["teras"][tera.strip()] += 1
                
            # Thống kê Tính cách (Nature)
            nature = pm.get("nature")
            if nature and nature.strip() and nature.lower() != "none":
                poke_details[poke_name]["natures"][nature.strip()] += 1
                
            # Thống kê Chiêu thức (Moves/Attacks)
            attacks = pm.get("attacks", [])
            for move in attacks:
                if move and move.strip() and move.lower() != "none":
                    poke_details[poke_name]["moves"][move.strip()] += 1

    if n_teams == 0:
        print("\n[CẢNH BÁO] Không tìm thấy đội hình (decklist) nào được công khai trong bảng xếp hạng.", file=sys.stderr)
        print("Giải đấu có thể chưa bắt đầu, hoặc người chơi chưa gửi đội hình, hoặc ban tổ chức chưa công khai đội hình.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Tổng số đội hình phân tích thành công: {n_teams} / {total_players} người chơi.")
    
    # 5. Tổng hợp và sắp xếp
    sorted_pokemon = sort_counter(pokemon_counts)
    
    # Tạo cấu trúc dữ liệu JSON để xuất bản
    usage_json_data = {
        "tournament_id": tour_id,
        "tournament_name": tour_name,
        "date": tour_date,
        "format": tour_format,
        "total_players": total_players,
        "teams_analyzed": n_teams,
        "pokemon_usage": []
    }
    
    for rank, (poke_name, count) in enumerate(sorted_pokemon, 1):
        pct = (count / n_teams) * 100
        details_entry = poke_details.get(poke_name, {})
        
        # Sắp xếp các chỉ số chi tiết của từng Pokemon
        items_list = [{"name": item, "count": cnt, "percentage": (cnt / count) * 100} for item, cnt in sort_counter(details_entry["items"])]
        abilities_list = [{"name": ab, "count": cnt, "percentage": (cnt / count) * 100} for ab, cnt in sort_counter(details_entry["abilities"])]
        moves_list = [{"name": mv, "count": cnt, "percentage": (cnt / count) * 100} for mv, cnt in sort_counter(details_entry["moves"])]
        teras_list = [{"name": tr, "count": cnt, "percentage": (cnt / count) * 100} for tr, cnt in sort_counter(details_entry["teras"])]
        natures_list = [{"name": nt, "count": cnt, "percentage": (cnt / count) * 100} for nt, cnt in sort_counter(details_entry["natures"])]
        forms_list = [{"name": f, "count": cnt, "percentage": (cnt / count) * 100} for f, cnt in sort_counter(details_entry.get("forms", {}))]
        
        usage_json_data["pokemon_usage"].append({
            "rank": rank,
            "name": poke_name,
            "count": count,
            "percentage": pct,
            "items": items_list,
            "abilities": abilities_list,
            "moves": moves_list,
            "teras": teras_list,
            "natures": natures_list,
            "forms": forms_list
        })
        
    # 6. Tạo file Markdown báo cáo
    safe_tour_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', tour_name.replace(" ", "_"))
    
    os.makedirs(output_dir, exist_ok=True)
    md_filename = os.path.join(output_dir, f"{safe_tour_name}_usage.md")
    json_filename = os.path.join(output_dir, f"{safe_tour_name}_usage.json")
    
    # Viết nội dung Markdown
    md_content = []
    md_content.append(f"# Báo cáo Usage Statistics - {tour_name}")
    md_content.append(f"**Ngày diễn ra:** {tour_date} | **Thể thức:** {tour_format}")
    md_content.append(f"**Số lượng người chơi:** {total_players} | **Số đội hình phân tích:** {n_teams} ({n_teams/total_players*100:.1f}%)")
    md_content.append("\n## Bảng xếp hạng Pokemon Usage\n")
    md_content.append("| Hạng | Pokemon | Số lượng | Tỷ lệ sử dụng (%) |")
    md_content.append("| :---: | :--- | :---: | :---: |")
    
    for item in usage_json_data["pokemon_usage"]:
        md_content.append(f"| {item['rank']} | **{item['name']}** | {item['count']} | {item['percentage']:.2f}% |")
        
    md_content.append("\n## Chi tiết cách xây dựng Pokemon (Pokemon Build Breakdown)\n")
    md_content.append(f"*Hiển thị chi tiết top {args.limit if args.limit > 0 else 'tất cả'} Pokemon có tỷ lệ sử dụng cao nhất.*\n")
    
    limit = args.limit if args.limit > 0 else len(usage_json_data["pokemon_usage"])
    for idx, item in enumerate(usage_json_data["pokemon_usage"][:limit]):
        poke_name = item["name"]
        md_content.append(f"### {idx+1}. {poke_name} (Sử dụng: {item['count']} lần - {item['percentage']:.2f}%)")
        
        # Thống kê phân bổ dạng Pokémon/Mega nếu có nhiều dạng
        non_base_forms = [f for f in item.get("forms", []) if f["name"] != "Base"]
        if len(item.get("forms", [])) > 1 or non_base_forms:
            forms_str = ", ".join([f"{f['name']}: {f['percentage']:.1f}%" for f in item["forms"]])
            md_content.append(f"**Forms/Mega Variants:** {forms_str}\n")
            
        # Tạo bảng so sánh chi tiết
        md_content.append("\n<details><summary>Xem chi tiết Build</summary>\n")
        
        # Cột: Vật phẩm & Đặc tính & Hệ Tera
        md_content.append("| Vật phẩm (Items) | Đặc tính (Abilities) | Hệ Tera (Tera Types) |")
        md_content.append("| :--- | :--- | :--- |")
        
        max_rows = max(len(item["items"]), len(item["abilities"]), len(item["teras"]))
        for r in range(max_rows):
            it_str = f"{item['items'][r]['name']} ({item['items'][r]['percentage']:.1f}%)" if r < len(item["items"]) else ""
            ab_str = f"{item['abilities'][r]['name']} ({item['abilities'][r]['percentage']:.1f}%)" if r < len(item["abilities"]) else ""
            te_str = f"{item['teras'][r]['name']} ({item['teras'][r]['percentage']:.1f}%)" if r < len(item["teras"]) else ""
            md_content.append(f"| {it_str} | {ab_str} | {te_str} |")
            
        md_content.append("\n| Chiêu thức (Moves) | Tính cách (Natures) | |")
        md_content.append("| :--- | :--- | :--- |")
        
        max_rows_2 = max(len(item["moves"]), len(item["natures"]))
        for r in range(max_rows_2):
            mv_str = f"{item['moves'][r]['name']} ({item['moves'][r]['percentage']:.1f}%)" if r < len(item["moves"]) else ""
            nt_str = f"{item['natures'][r]['name']} ({item['natures'][r]['percentage']:.1f}%)" if r < len(item["natures"]) else ""
            md_content.append(f"| {mv_str} | {nt_str} | |")
            
        md_content.append("\n</details>\n")
        
    # Ghi ra file MD
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    # Ghi ra file JSON
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(usage_json_data, f, ensure_ascii=False, indent=2)
        
    # Ghi ra file HTML
    html_filename = os.path.join(output_dir, f"{safe_tour_name}_usage.html")
    write_html_report(usage_json_data, html_filename)
        
    print(f"\n==================================================")
    print(f" THÀNH CÔNG: Đã tạo và lưu các báo cáo Usage tại:")
    print(f" -> Markdown: {os.path.abspath(md_filename)}")
    print(f" -> JSON: {os.path.abspath(json_filename)}")
    print(f" -> HTML: {os.path.abspath(html_filename)}")
    print(f"==================================================")
    
    # Hiển thị Top 10 Pokemon Usage ra console
    print("\n### TOP 10 POKEMON USAGE:")
    print(f"| Hạng | Pokemon | Số lượng | Tỷ lệ sử dụng (%) |")
    print(f"| :---: | :--- | :---: | :---: |")
    for item in usage_json_data["pokemon_usage"][:10]:
        print(f"| {item['rank']} | {item['name']} | {item['count']} | {item['percentage']:.2f}% |")


if __name__ == "__main__":
    main()
