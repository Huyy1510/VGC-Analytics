#!/usr/bin/env python3
import json
import os
import sys
import argparse
import re

def parse_args():
    parser = argparse.ArgumentParser(description="So sánh chỉ số usage và dịch chuyển meta giữa 2 tuần giải đấu Pokemon VGC.")
    parser.add_argument("old_json", help="Đường dẫn đến file JSON của tuần cũ/giải cũ")
    parser.add_argument("new_json", help="Đường dẫn đến file JSON của tuần mới/giải mới")
    parser.add_argument("-o", "--output-dir", default=".", help="Thư mục lưu báo cáo kết quả (mặc định: thư mục hiện tại)")
    parser.add_argument("-l", "--limit", type=int, default=10, help="Số lượng Pokemon hàng đầu hiển thị chi tiết biến động build (mặc định: 10, truyền -1 để phân tích tất cả)")
    return parser.parse_args()


def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file JSON {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def compare_metrics(old_list, new_list):
    """
    So sánh hai danh sách thuộc tính (items, moves, v.v.) của một Pokemon.
    Trả về danh sách các thay đổi dưới dạng dict: { name, old_pct, new_pct, diff }
    Được sắp xếp theo tỷ lệ mới giảm dần, các phần tử bị biến mất xếp cuối cùng.
    """
    old_dict = {x["name"]: x["percentage"] for x in old_list}
    new_dict = {x["name"]: x["percentage"] for x in new_list}
    
    all_names = set(old_dict.keys()).union(set(new_dict.keys()))
    comparison = []
    
    for name in all_names:
        old_pct = old_dict.get(name, 0.0)
        new_pct = new_dict.get(name, 0.0)
        diff = new_pct - old_pct
        comparison.append({
            "name": name,
            "old_percentage": old_pct,
            "new_percentage": new_pct,
            "diff": diff
        })
        
    # Sắp xếp: Tỷ lệ mới giảm dần, nếu cùng bằng 0 thì sắp xếp theo chênh lệch giảm dần
    comparison.sort(key=lambda x: (x["new_percentage"], abs(x["diff"])), reverse=True)
    return comparison


def format_diff_pct(diff):
    if diff > 0:
        return f"+{diff:.2f}%"
    elif diff < 0:
        return f"{diff:.2f}%"
    return "0.00%"


def format_rank_change(old_rank, new_rank):
    if old_rank is None and new_rank is not None:
        return "*New*"
    if old_rank is not None and new_rank is None:
        return "*Dropped*"
    if old_rank is None and new_rank is None:
        return "▬"
    
    diff = old_rank - new_rank  # Hạng nhỏ hơn là cao hơn (ví dụ: hạng 4 lên 1 tức là +3)
    if diff > 0:
        return f"▲ {diff}"
    elif diff < 0:
        return f"▼ {abs(diff)}"
    return "▬"


def main():
    args = parse_args()
    
    # 1. Đọc dữ liệu JSON
    old_data = load_json(args.old_json)
    new_data = load_json(args.new_json)
    
    old_name = old_data.get("tournament_name", "Giải đấu cũ")
    new_name = new_data.get("tournament_name", "Giải đấu mới")
    
    print(f"Đang so sánh:")
    print(f" -> Cũ (Tuần trước): {old_name} ({old_data.get('date', 'N/A')})")
    print(f" -> Mới (Tuần này): {new_name} ({new_data.get('date', 'N/A')})")
    
    # 2. Ánh xạ Pokemon
    old_pokes = {p["name"]: p for p in old_data.get("pokemon_usage", [])}
    new_pokes = {p["name"]: p for p in new_data.get("pokemon_usage", [])}
    
    all_poke_names = set(old_pokes.keys()).union(set(new_pokes.keys()))
    
    compared_pokes = []
    
    for name in all_poke_names:
        o_poke = old_pokes.get(name, {})
        n_poke = new_pokes.get(name, {})
        
        old_pct = o_poke.get("percentage", 0.0)
        new_pct = n_poke.get("percentage", 0.0)
        old_count = o_poke.get("count", 0)
        new_count = n_poke.get("count", 0)
        
        old_rank = o_poke.get("rank")
        new_rank = n_poke.get("rank")
        
        pct_diff = new_pct - old_pct
        
        # So sánh chi tiết build
        items_diff = compare_metrics(o_poke.get("items", []), n_poke.get("items", []))
        abilities_diff = compare_metrics(o_poke.get("abilities", []), n_poke.get("abilities", []))
        moves_diff = compare_metrics(o_poke.get("moves", []), n_poke.get("moves", []))
        teras_diff = compare_metrics(o_poke.get("teras", []), n_poke.get("teras", []))
        natures_diff = compare_metrics(o_poke.get("natures", []), n_poke.get("natures", []))
        
        compared_pokes.append({
            "name": name,
            "old_rank": old_rank,
            "new_rank": new_rank,
            "old_count": old_count,
            "new_count": new_count,
            "old_percentage": old_pct,
            "new_percentage": new_pct,
            "percentage_diff": pct_diff,
            "rank_change_str": format_rank_change(old_rank, new_rank),
            "items": items_diff,
            "abilities": abilities_diff,
            "moves": moves_diff,
            "teras": teras_diff,
            "natures": natures_diff
        })
        
    # Sắp xếp danh sách chung: Ưu tiên các con nằm trong bảng mới theo hạng mới tăng dần.
    # Các con bị loại khỏi bảng mới sẽ được xếp ở cuối theo hạng cũ tăng dần.
    def sort_key(x):
        n_rank = x["new_rank"]
        o_rank = x["old_rank"]
        if n_rank is not None:
            return (0, n_rank)
        return (1, o_rank if o_rank is not None else 9999)
        
    compared_pokes.sort(key=sort_key)
    
    # 3. Tìm Winners & Losers (Biến động tỷ lệ phần trăm lớn nhất)
    # Lọc các Pokemon có xuất hiện ở ít nhất 1 tuần
    valid_diffs = [p for p in compared_pokes if p["old_percentage"] > 0 or p["new_percentage"] > 0]
    winners = sorted(valid_diffs, key=lambda x: x["percentage_diff"], reverse=True)[:5]
    losers = sorted(valid_diffs, key=lambda x: x["percentage_diff"])[:5]
    # Lọc bỏ những losers có chênh lệch >= 0 (đề phòng meta ít thay đổi)
    losers = [l for l in losers if l["percentage_diff"] < 0]
    # Lọc bỏ winners có chênh lệch <= 0
    winners = [w for w in winners if w["percentage_diff"] > 0]
    
    # 4. Ghi cấu trúc kết quả ra JSON
    comparison_results = {
        "old_tournament": {
            "name": old_name,
            "date": old_data.get("date", "N/A"),
            "format": old_data.get("format", "N/A"),
            "total_players": old_data.get("total_players", 0),
            "teams_analyzed": old_data.get("teams_analyzed", 0),
        },
        "new_tournament": {
            "name": new_name,
            "date": new_data.get("date", "N/A"),
            "format": new_data.get("format", "N/A"),
            "total_players": new_data.get("total_players", 0),
            "teams_analyzed": new_data.get("teams_analyzed", 0),
        },
        "pokemon_shifts": compared_pokes
    }
    
    safe_old_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', old_name.replace(" ", "_"))
    safe_new_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', new_name.replace(" ", "_"))
    
    os.makedirs(args.output_dir, exist_ok=True)
    md_filename = os.path.join(args.output_dir, f"{safe_old_name}_vs_{safe_new_name}_comparison.md")
    json_filename = os.path.join(args.output_dir, f"{safe_old_name}_vs_{safe_new_name}_comparison.json")
    
    # 5. Viết nội dung Markdown
    md_content = []
    md_content.append(f"# Báo cáo So sánh Dịch chuyển Meta và Usage")
    md_content.append(f"So sánh giữa 2 giải đấu:")
    md_content.append(f"- **Giải đấu Cũ (Tuần trước):** {old_name} ({old_data.get('date', 'N/A')})")
    md_content.append(f"- **Giải đấu Mới (Tuần này):** {new_name} ({new_data.get('date', 'N/A')})")
    md_content.append("\n---")
    
    # Bảng so sánh tổng quan chỉ số giải đấu
    md_content.append("\n## 1. So sánh quy mô giải đấu\n")
    md_content.append("| Chỉ số | Giải đấu Cũ | Giải đấu Mới | Biến động |")
    md_content.append("| :--- | :---: | :---: | :---: |")
    
    player_diff = new_data.get('total_players', 0) - old_data.get('total_players', 0)
    player_diff_str = f"+{player_diff}" if player_diff > 0 else str(player_diff)
    md_content.append(f"| **Số người chơi đăng ký** | {old_data.get('total_players', 0)} | {new_data.get('total_players', 0)} | {player_diff_str} |")
    
    teams_diff = new_data.get('teams_analyzed', 0) - old_data.get('teams_analyzed', 0)
    teams_diff_str = f"+{teams_diff}" if teams_diff > 0 else str(teams_diff)
    md_content.append(f"| **Số đội hình công khai** | {old_data.get('teams_analyzed', 0)} | {new_data.get('teams_analyzed', 0)} | {teams_diff_str} |")
    
    # Xu hướng Winners & Losers
    md_content.append("\n## 2. Xu hướng dịch chuyển meta mạnh nhất\n")
    
    if winners:
        md_content.append("### Pokémon tăng trưởng mạnh nhất (Winners) 📈")
        for w in winners:
            md_content.append(f"- **{w['name']}**: {w['old_percentage']:.2f}% -> {w['new_percentage']:.2f}% ({format_diff_pct(w['percentage_diff'])})")
    
    if losers:
        md_content.append("\n### Pokémon suy giảm mạnh nhất (Losers) 📉")
        for l in losers:
            md_content.append(f"- **{l['name']}**: {l['old_percentage']:.2f}% -> {l['new_percentage']:.2f}% ({format_diff_pct(l['percentage_diff'])})")
            
    # Bảng xếp hạng so sánh
    md_content.append("\n## 3. Bảng xếp hạng so sánh tỷ lệ sử dụng (Usage Shifts)\n")
    md_content.append("| Hạng Mới | Biến động Hạng | Pokémon | Usage Cũ (%) | Usage Mới (%) | Chênh lệch |")
    md_content.append("| :---: | :---: | :--- | :---: | :---: | :---: |")
    
    for p in compared_pokes:
        rank_str = str(p["new_rank"]) if p["new_rank"] is not None else "-"
        change_str = p["rank_change_str"]
        
        # Thêm màu/định dạng chữ cho biến động mạnh
        if "▲" in change_str or "New" in change_str:
            change_str = f"**{change_str}**"
        elif "▼" in change_str or "Dropped" in change_str:
            change_str = f"*{change_str}*"
            
        old_pct_str = f"{p['old_percentage']:.2f}%" if p["old_percentage"] > 0 else "-"
        new_pct_str = f"{p['new_percentage']:.2f}%" if p["new_percentage"] > 0 else "-"
        
        diff_str = format_diff_pct(p["percentage_diff"])
        if p["percentage_diff"] > 0:
            diff_str = f"**{diff_str}**"
        elif p["percentage_diff"] < 0:
            diff_str = f"*{diff_str}*"
            
        md_content.append(f"| {rank_str} | {change_str} | **{p['name']}** | {old_pct_str} | {new_pct_str} | {diff_str} |")
        
    # Chi tiết biến động Build Pokémon
    md_content.append("\n## 4. Chi tiết biến động cách xây dựng Pokémon (Build Shifts)\n")
    md_content.append(f"*Phân tích sự thay đổi chi tiết (vật phẩm, đặc tính, chiêu thức, hệ Tera) của top {args.limit if args.limit > 0 else 'tất cả'} Pokémon.*\n")
    
    limit = args.limit if args.limit > 0 else len(compared_pokes)
    # Lọc những con có mặt trong giải đấu mới để so sánh build
    active_compared = [p for p in compared_pokes if p["new_percentage"] > 0][:limit]
    
    for idx, p in enumerate(active_compared):
        poke_name = p["name"]
        md_content.append(f"### {idx+1}. {poke_name} (Thay đổi Usage: {format_diff_pct(p['percentage_diff'])})")
        md_content.append("\n<details><summary>Xem chi tiết dịch chuyển Build</summary>\n")
        
        # Hàm con helper để in danh sách thay đổi có chênh lệch
        def format_metric_comparison(comp_list):
            lines = []
            for item in comp_list:
                name = item["name"]
                old = item["old_percentage"]
                new = item["new_percentage"]
                diff = item["diff"]
                
                # Bỏ qua nếu không có sự thay đổi nào và tỷ lệ sử dụng quá thấp (< 1%)
                if old == 0.0 and new == 0.0:
                    continue
                    
                diff_str = format_diff_pct(diff)
                if diff > 2.0:
                    diff_str = f"**{diff_str}**"
                elif diff < -2.0:
                    diff_str = f"*{diff_str}*"
                    
                old_str = f"{old:.1f}%" if old > 0 else "-"
                new_str = f"{new:.1f}%" if new > 0 else "-"
                
                lines.append(f"| {name} | {old_str} | {new_str} | {diff_str} |")
            return lines
            
        # In so sánh Vật phẩm
        md_content.append("#### Vật phẩm (Items)")
        md_content.append("| Vật phẩm | Tỷ lệ Cũ | Tỷ lệ Mới | Thay đổi |")
        md_content.append("| :--- | :---: | :---: | :---: |")
        item_lines = format_metric_comparison(p["items"])
        if item_lines:
            md_content.extend(item_lines)
        else:
            md_content.append("| (Không có vật phẩm nào được sử dụng) | - | - | - |")
            
        # In so sánh Chiêu thức
        md_content.append("\n#### Chiêu thức (Moves)")
        md_content.append("| Chiêu thức | Tỷ lệ Cũ | Tỷ lệ Mới | Thay đổi |")
        md_content.append("| :--- | :---: | :---: | :---: |")
        move_lines = format_metric_comparison(p["moves"])
        if move_lines:
            md_content.extend(move_lines)
        else:
            md_content.append("| (Không có chiêu thức nào được sử dụng) | - | - | - |")
            
        # In so sánh Đặc tính & Hệ Tera
        md_content.append("\n#### Đặc tính & Hệ Tera (Abilities & Tera Types)")
        md_content.append("| Thuộc tính | Tỷ lệ Cũ | Tỷ lệ Mới | Thay đổi |")
        md_content.append("| :--- | :---: | :---: | :---: |")
        ability_lines = format_metric_comparison(p["abilities"])
        if ability_lines:
            md_content.extend(ability_lines)
        tera_lines = format_metric_comparison(p["teras"])
        if tera_lines:
            md_content.extend(tera_lines)
            
        md_content.append("\n</details>\n")
        
    # Ghi ra file MD
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    # Ghi ra file JSON
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, ensure_ascii=False, indent=2)
        
    print(f"\n==================================================")
    print(f" THÀNH CÔNG: Đã tạo và lưu báo cáo so sánh tại:")
    print(f" -> Markdown: {os.path.abspath(md_filename)}")
    print(f" -> JSON: {os.path.abspath(json_filename)}")
    print(f"==================================================")
    
    # Hiển thị tóm tắt ra console
    print(f"\n### XU HƯỚNG DỊCH CHUYỂN META NỔI BẬT:")
    if winners:
        print("Tăng trưởng mạnh nhất (Winners):")
        for w in winners[:3]:
            print(f" - {w['name']}: {w['old_percentage']:.1f}% -> {w['new_percentage']:.1f}% ({format_diff_pct(w['percentage_diff'])})")
    if losers:
        print("Suy giảm mạnh nhất (Losers):")
        for l in losers[:3]:
            print(f" - {l['name']}: {l['old_percentage']:.1f}% -> {l['new_percentage']:.1f}% ({format_diff_pct(l['percentage_diff'])})")


if __name__ == "__main__":
    main()
