#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import ssl
import re
import os
import sys
import argparse

# Khởi tạo SSL context không xác thực chứng chỉ (để tránh lỗi SSL trên macOS)
ssl_context = ssl._create_unverified_context()

# Đường dẫn đến các file ánh xạ tên
script_dir = os.path.dirname(os.path.abspath(__file__))
POKEMON_MAP_PATH = os.path.join(script_dir, "pokemon_name_mapping.json")
ITEM_MAP_PATH = os.path.join(script_dir, "item_name_mapping.json")

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


def extract_tournament_id(input_str):
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
            req = urllib.request.Request(input_str, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ssl_context) as response:
                html = response.read().decode('utf-8')
            
            # Tìm tất cả chuỗi hex 24 ký tự trong HTML
            hex_ids = re.findall(r'[0-9a-f]{24}', html)
            if hex_ids:
                resolved_id = hex_ids[0]
                print(f"Tìm thấy ID giải đấu: {resolved_id}")
                return resolved_id
        except Exception as e:
            print(f"Lỗi khi tải trang để tìm ID giải đấu: {e}", file=sys.stderr)
            
    return None


def get_api_data(url):
    """Gửi yêu cầu GET đến API Limitless"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ssl_context) as response:
        return json.loads(response.read().decode('utf-8'))


def to_showdown_format(pm):
    """Chuyển đổi một Pokemon JSON sang định dạng Showdown text"""
    name = pm.get("name")
    name = name.strip() if name else ""
    if not name:
        return ""
        
    lines = []
    item = pm.get("item")
    item = item.strip() if item else ""
    if item:
        lines.append(f"{name} @ {item}")
    else:
        lines.append(name)
        
    ability = pm.get("ability")
    ability = ability.strip() if ability else ""
    if ability:
        lines.append(f"Ability: {ability}")
        
    lines.append("Level: 50")
    
    tera = pm.get("tera")
    tera = tera.strip() if tera else ""
    if tera and tera != "None":
        lines.append(f"Tera Type: {tera}")
        
    nature = pm.get("nature")
    nature = nature.strip() if nature else ""
    if nature and nature != "None":
        lines.append(f"{nature} Nature")
        
    moves = pm.get("attacks", [])
    for move in moves:
        move = move.strip() if move else ""
        if move:
            lines.append(f"- {move}")
            
    return "\n".join(lines)


def create_pokepaste(player_name, tournament_name, team_text):
    """Tải đội hình lên pokepast.es và trả về URL"""
    url = "https://pokepast.es/create"
    data = {
        "title": f"Đội hình {player_name} - {tournament_name}",
        "author": "Limitless Auto Generator",
        "paste": team_text
    }
    
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=encoded_data, method='POST')
    
    try:
        # Sử dụng ssl_context để tránh lỗi chứng chỉ SSL trên macOS
        with urllib.request.urlopen(req, context=ssl_context) as response:
            final_url = response.geturl()
            return final_url
    except Exception as e:
        print(f"Lỗi khi tạo PokePaste cho {player_name}: {e}", file=sys.stderr)
        return None


def map_pokemon_name(name):
    """Ánh xạ tên Pokemon theo từ điển hoặc định dạng chuẩn của joaoabel"""
    if not name:
        return ""
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Quy tắc chung cho các dạng vùng miền (Regional forms)
    # Ví dụ: "Hisuian Arcanine" -> "Arcanine-Hisui"
    if name_lower.startswith("hisuian "):
        return name_clean[8:] + "-Hisui"
    if name_lower.startswith("alolan "):
        return name_clean[7:] + "-Alola"
    if name_lower.startswith("galarian "):
        return name_clean[9:] + "-Galar"
    if name_lower.startswith("paldean "):
        return name_clean[8:] + "-Paldea"
        
    # Chuẩn hóa chuỗi trước khi tra cứu
    # "Urshifu (Rapid Strike)" -> "urshifu-rapid-strike"
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


def main():
    parser = argparse.ArgumentParser(description="Tự động hóa Top 8 Pokemon VGC Standings & PokePastes.")
    parser.add_argument("tournament", help="URL giải đấu Limitless hoặc ID giải đấu (24 ký tự hex)")
    parser.add_argument("-o", "--output", help="Đường dẫn lưu hình ảnh kết quả (mặc định: [tên-giải-đấu].png)")
    
    args = parser.parse_args()
    
    # 1. Trích xuất ID giải đấu
    tour_id = extract_tournament_id(args.tournament)
    if not tour_id:
        print("Lỗi: Không tìm thấy ID giải đấu hợp lệ (phải chứa chuỗi hex 24 ký tự hoặc URL hợp lệ).", file=sys.stderr)
        sys.exit(1)
        
    print(f"Đang xử lý giải đấu với ID: {tour_id}...")
    
    # 2. Lấy thông tin chi tiết giải đấu
    try:
        details = get_api_data(f"https://play.limitlesstcg.com/api/tournaments/{tour_id}/details")
    except Exception as e:
        print(f"Lỗi khi lấy thông tin chi tiết giải đấu: {e}", file=sys.stderr)
        sys.exit(1)
        
    tour_name = details.get("name", "Tournament")
    tour_date_raw = details.get("date", "")
    tour_format = details.get("format", "VGC")
    total_players = details.get("players", 0)
    
    # Định dạng ngày DD/MM/YYYY
    tour_date = "04/06/2026"
    if tour_date_raw:
        try:
            parts = tour_date_raw.split("T")[0].split("-")
            tour_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
            
    print(f"Giải đấu: {tour_name}")
    print(f"Ngày đấu: {tour_date} | Thể thức: {tour_format} | Người chơi: {total_players}")
    
    # 3. Lấy bảng xếp hạng
    print("Đang tải bảng xếp hạng...")
    try:
        standings = get_api_data(f"https://play.limitlesstcg.com/api/tournaments/{tour_id}/standings")
    except Exception as e:
        print(f"Lỗi khi tải bảng xếp hạng: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Lọc ra Top 8 người chơi
    top_8 = []
    for p in standings:
        placing = p.get("placing")
        if placing is not None and placing <= 8:
            top_8.append(p)
            
    # Sắp xếp theo thứ hạng
    top_8.sort(key=lambda x: x.get("placing", 999))
    
    if not top_8:
        print("Không tìm thấy người chơi nào trong Top 8 có thứ hạng hợp lệ. Giải đấu có thể chưa kết thúc hoặc chưa công bố standings.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Tìm thấy {len(top_8)} người chơi trong Top 8. Bắt đầu xử lý đội hình...")
    
    # 4. Tạo PokePastes và định dạng dữ liệu cho Generator
    generator_players = []
    markdown_results = []
    
    # Định dạng ánh xạ format
    format_map = {
        "M-B": "VGC 2026 - Regulation M-B",
        "M-A": "VGC 2026 - Regulation M-A",
        "J": "VGC 2025 - Regulation J",
        "I": "VGC 2025 - Regulation I",
        "H": "VGC 2025 - Regulation H",
        "G": "VGC 2024 - Regulation G",
        "F": "VGC 2025 - Regulation F",
        "E": "VGC 2024 - Regulation E",
        "D": "VGC 2023 - Regulation D",
        "C": "VGC 2023 - Regulation C",
        "B": "VGC 2023 - Regulation B",
        "A": "VGC 2023 - Regulation A",
    }
    mapped_format = format_map.get(tour_format, "VGC 2026 - Regulation M-B")
    
    for idx, p in enumerate(top_8):
        player_name = p.get("name", "Unknown")
        rank = p.get("placing", idx + 1)
        rec = p.get("record", {})
        record_str = f"{rec.get('wins', 0)}-{rec.get('losses', 0)}"
        
        country = p.get("country")
        country = country.strip() if country else ""
            
        print(f"[{rank}/8] Đang xử lý người chơi: {player_name} ({country}) ({record_str})...")
        
        # Tạo Showdown text
        pokemon_list = []
        showdown_blocks = []
        
        for pm in p.get("decklist", []):
            showdown_block = to_showdown_format(pm)
            if showdown_block:
                showdown_blocks.append(showdown_block)
                
            # Tạo bản lưu để gửi tới joaoabel (với tên Pokemon và item đã được ánh xạ)
            raw_p_name = pm.get("name", "")
            raw_item_name = pm.get("item", "")
            
            # Kiểm tra xem có phải là Mega Evolution hay không dựa trên vật phẩm
            is_mega = False
            item_clean = raw_item_name.strip().lower() if raw_item_name else ""
            if item_clean and item_clean != "eviolite" and (item_clean.endswith("ite") or "ite x" in item_clean or "ite y" in item_clean or "ite-x" in item_clean or "ite-y" in item_clean):
                is_mega = True
                
            p_name_for_mapping = raw_p_name
            if is_mega:
                if "charizardite x" in item_clean:
                    p_name_for_mapping = f"{raw_p_name} Mega X"
                elif "charizardite y" in item_clean:
                    p_name_for_mapping = f"{raw_p_name} Mega Y"
                elif "mewtwoite x" in item_clean:
                    p_name_for_mapping = f"{raw_p_name} Mega X"
                elif "mewtwoite y" in item_clean:
                    p_name_for_mapping = f"{raw_p_name} Mega Y"
                else:
                    p_name_for_mapping = f"{raw_p_name} Mega"
            
            mapped_p_name = map_pokemon_name(p_name_for_mapping)
            
            # Nếu tên sau khi map rơi vào danh sách không được hỗ trợ bởi generator API, quay về tên gốc (không Mega)
            unsupported_megas = {
                "staraptor-mega", "raichu-mega", "raichu-mega-x", "raichu-mega-y",
                "eelektross-mega", "malamar-mega", "barbaracle-mega", "falinks-mega"
            }
            if mapped_p_name and mapped_p_name.lower().replace(" ", "-") in unsupported_megas:
                mapped_p_name = map_pokemon_name(raw_p_name)
                
            mapped_item_name = map_item_name(raw_item_name)
            
            # debug map names
            if raw_p_name != mapped_p_name and mapped_p_name:
                print(f"  Ánh xạ Pokemon: '{raw_p_name}' -> '{mapped_p_name}'")
            if raw_item_name != mapped_item_name and mapped_item_name:
                print(f"  Ánh xạ Vật phẩm: '{raw_item_name}' -> '{mapped_item_name}'")
                
            pokemon_list.append({
                "name": mapped_p_name,
                "item": mapped_item_name,
                "teratype": pm.get("tera", "") or ""
            })
            
        # Bổ sung đủ 6 slot Pokemon
        while len(pokemon_list) < 6:
            pokemon_list.append({"name": "", "item": "", "teratype": ""})
            
        # Tạo PokePaste
        pokepaste_url = "N/A"
        if showdown_blocks:
            team_text = "\n\n".join(showdown_blocks)
            created_url = create_pokepaste(player_name, tour_name, team_text)
            if created_url:
                pokepaste_url = created_url
                print(f"  -> PokePaste: {pokepaste_url}")
                
        generator_players.append({
            "name": player_name,
            "record": record_str,
            "flag": country,
            "pokemon": pokemon_list
        })
        
        markdown_results.append({
            "rank": rank,
            "name": player_name,
            "flag": country,
            "record": record_str,
            "paste": pokepaste_url
        })
        
    # 5. Tạo ảnh bảng xếp hạng thông qua API joaoabel
    print("Đang gửi yêu cầu tạo hình ảnh bảng xếp hạng Top 8...")
    
    payload = {
        "tour_name": tour_name,
        "tour_type": "GRASSROOTS",
        "date": tour_date,
        "format": mapped_format,
        "game": "VGC",
        "divisions": {
            "junior": 0,
            "senior": 0,
            "master": total_players
        },
        "players": generator_players,
        "show_logo": True,
        "show_background": True
    }
    
    gen_url = "https://api.generator.joaoabel.pt/topcut/png"
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(gen_url, data=req_data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, context=ssl_context) as response:
            img_data = response.read()
            
        # Xác định đường dẫn lưu file ảnh
        if args.output:
            out_file = args.output
        else:
            # Tạo tên file an toàn từ tên giải đấu
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', tour_name.replace(" ", "_"))
            out_file = f"{safe_name}_top8.png"
            
        with open(out_file, "wb") as f:
            f.write(img_data)
            
        print(f"\n==================================================")
        print(f" THÀNH CÔNG: Đã tạo và lưu ảnh bảng xếp hạng tại:")
        print(f" -> {os.path.abspath(out_file)}")
        print(f"==================================================\n")
        
    except urllib.error.HTTPError as e:
        print(f"Lỗi từ Generator API (HTTP {e.code}):", file=sys.stderr)
        try:
            print("Chi tiết lỗi:", e.read().decode('utf-8'), file=sys.stderr)
        except Exception:
            pass
    except Exception as e:
        print(f"Lỗi kết nối hoặc xử lý ảnh bảng xếp hạng: {e}", file=sys.stderr)
        
    # 6. In báo cáo tóm tắt Markdown
    print("### BÁO CÁO KẾT QUẢ TOP 8 GIẢI ĐẤU")
    print(f"**Giải đấu:** {tour_name}")
    print(f"**Ngày:** {tour_date} | **Thể thức:** {tour_format} | **Tổng người chơi:** {total_players}")
    print("\n| Hạng | Tên người chơi | Quốc gia | Record | PokePaste Link |")
    print("| :---: | :--- | :---: | :---: | :--- |")
    for res in markdown_results:
        flag_str = f"🇺🇸 ({res['flag']})" if res['flag'] == "US" else f"({res['flag']})" if res['flag'] else "-"
        print(f"| {res['rank']} | {res['name']} | {flag_str} | {res['record']} | [{res['paste']}]({res['paste']}) |")
    print("\nQuy trình hoàn tất thành công!")


if __name__ == "__main__":
    main()
