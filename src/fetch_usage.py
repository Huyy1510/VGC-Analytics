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


def main():
    parser = argparse.ArgumentParser(description="Thu thập và phân tích chỉ số sử dụng (Usage Statistics) của giải đấu Limitless (hỗ trợ cả giải đấu Public và Private).")
    parser.add_argument("tournament", help="URL giải đấu Limitless hoặc ID giải đấu (24 ký tự hex)")
    parser.add_argument("-k", "--key", help="API Key của Limitless (hoặc thiết lập biến môi trường LIMITLESS_API_KEY)")
    parser.add_argument("-o", "--output-dir", help="Thư mục lưu kết quả báo cáo (mặc định: thư mục results/ ở thư mục gốc dự án)")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Số lượng Pokemon hàng đầu hiển thị chi tiết (mặc định: 20, truyền -1 để hiển thị tất cả)")
    
    args = parser.parse_args()
    
    output_dir = args.output_dir if args.output_dir else os.path.join(project_root, "results")
    
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
            if item_clean and item_clean != "eviolite" and (item_clean.endswith("ite") or "ite x" in item_clean or "ite y" in item_clean or "ite-x" in item_clean or "ite-y" in item_clean):
                is_mega = True
                
            p_name_for_mapping = raw_poke_name
            if is_mega:
                if "charizardite x" in item_clean:
                    p_name_for_mapping = f"{raw_poke_name} Mega X"
                elif "charizardite y" in item_clean:
                    p_name_for_mapping = f"{raw_poke_name} Mega Y"
                elif "mewtwoite x" in item_clean:
                    p_name_for_mapping = f"{raw_poke_name} Mega X"
                elif "mewtwoite y" in item_clean:
                    p_name_for_mapping = f"{raw_poke_name} Mega Y"
                else:
                    p_name_for_mapping = f"{raw_poke_name} Mega"
            
            poke_name = map_pokemon_name(p_name_for_mapping)
            
            # Nếu tên sau khi map rơi vào danh sách không được hỗ trợ bởi generator API, quay về tên gốc (không Mega)
            unsupported_megas = {
                "staraptor-mega", "raichu-mega", "raichu-mega-x", "raichu-mega-y",
                "eelektross-mega", "malamar-mega", "barbaracle-mega", "falinks-mega"
            }
            if poke_name and poke_name.lower().replace(" ", "-") in unsupported_megas:
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
                    "natures": Counter()
                }
                
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
        
        usage_json_data["pokemon_usage"].append({
            "rank": rank,
            "name": poke_name,
            "count": count,
            "percentage": pct,
            "items": items_list,
            "abilities": abilities_list,
            "moves": moves_list,
            "teras": teras_list,
            "natures": natures_list
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
        
    print(f"\n==================================================")
    print(f" THÀNH CÔNG: Đã tạo và lưu các báo cáo Usage tại:")
    print(f" -> Markdown: {os.path.abspath(md_filename)}")
    print(f" -> JSON: {os.path.abspath(json_filename)}")
    print(f"==================================================")
    
    # Hiển thị Top 10 Pokemon Usage ra console
    print("\n### TOP 10 POKEMON USAGE:")
    print(f"| Hạng | Pokemon | Số lượng | Tỷ lệ sử dụng (%) |")
    print(f"| :---: | :--- | :---: | :---: |")
    for item in usage_json_data["pokemon_usage"][:10]:
        print(f"| {item['rank']} | {item['name']} | {item['count']} | {item['percentage']:.2f}% |")


if __name__ == "__main__":
    main()
