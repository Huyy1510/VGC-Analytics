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
    parser.add_argument("-o", "--output-dir", help="Thư mục lưu báo cáo kết quả (mặc định: thư mục results/ ở thư mục gốc dự án)")
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


def write_html_comparison(data, filename):
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokémon VGC - Meta Shift Comparison Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0b0f19;
            --bg-card: #151d30;
            --bg-active: #1e293b;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border: #1e293b;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.15);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.15);
            --warning: #f59e0b;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 2rem;
            min-height: 100vh;
            line-height: 1.5;
        }
        
        .header-grid {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            gap: 2rem;
            background: linear-gradient(135deg, var(--bg-card) 0%, #1e1b4b 100%);
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }
        
        .tour-card {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        
        .tour-label {
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            font-weight: 700;
        }
        
        .tour-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffffff;
        }
        
        .tour-meta {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 0.3rem;
        }
        
        .meta-badge {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 0.25rem 0.6rem;
            border-radius: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        .vs-divider {
            font-size: 1.5rem;
            font-weight: 800;
            font-style: italic;
            background: linear-gradient(to right, #6366f1, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            padding: 0.5rem 1rem;
            background-color: rgba(255, 255, 255, 0.03);
            border-radius: 50%;
            border: 1px dashed var(--border);
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 1.25rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        
        .stat-card-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .stat-card-val {
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }
        
        .stat-delta {
            font-size: 0.85rem;
            font-weight: 600;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }
        
        .stat-delta.up {
            background-color: var(--success-glow);
            color: var(--success);
        }
        
        .stat-delta.down {
            background-color: var(--danger-glow);
            color: var(--danger);
        }
        
        .stat-delta.neutral {
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
        }
        
        .highlights-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2.5rem;
        }
        
        .highlight-card {
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        }
        
        .highlight-card.winners {
            border-top: 4px solid var(--success);
        }
        
        .highlight-card.losers {
            border-top: 4px solid var(--danger);
        }
        
        .highlight-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .highlight-list {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }
        
        .highlight-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.6rem 0.9rem;
            background-color: var(--bg-main);
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        
        .highlight-name {
            font-weight: 600;
        }
        
        .highlight-val {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }
        
        .pct-badge {
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-weight: 700;
            font-size: 0.8rem;
        }
        
        .pct-badge.up {
            background-color: var(--success-glow);
            color: var(--success);
        }
        
        .pct-badge.down {
            background-color: var(--danger-glow);
            color: var(--danger);
        }
        
        .controls-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }
        
        .search-wrapper {
            flex: 1;
            min-width: 250px;
        }
        
        .search-input {
            width: 100%;
            padding: 0.75rem 1.1rem;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s;
        }
        
        .search-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }
        
        .tabs-wrapper {
            display: flex;
            gap: 0.4rem;
            background-color: var(--bg-card);
            padding: 0.3rem;
            border-radius: 10px;
            border: 1px solid var(--border);
        }
        
        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 500;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .tab-btn:hover {
            color: var(--text-main);
        }
        
        .tab-btn.active {
            background-color: var(--bg-active);
            color: var(--primary);
            font-weight: 600;
        }
        
        .table-container {
            background-color: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            margin-bottom: 2rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        
        th {
            background-color: rgba(255, 255, 255, 0.02);
            padding: 1rem 1.25rem;
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        td {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.95rem;
        }
        
        .poke-row {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .poke-row:hover {
            background-color: rgba(99, 102, 241, 0.04);
        }
        
        .poke-row.active {
            background-color: rgba(99, 102, 241, 0.08);
        }
        
        .rank-cell {
            font-weight: 700;
            color: var(--text-muted);
            width: 80px;
        }
        
        .rank-change {
            font-weight: 600;
            width: 120px;
        }
        .rank-change.up {
            color: var(--success);
        }
        .rank-change.down {
            color: var(--danger);
        }
        .rank-change.new {
            color: var(--primary);
            font-style: italic;
        }
        .rank-change.dropped {
            color: var(--text-muted);
            font-style: italic;
        }
        
        .name-cell {
            font-weight: 600;
            color: #ffffff;
        }
        
        .pct-cell {
            font-weight: 600;
            width: 130px;
        }
        
        .diff-cell {
            font-weight: 700;
            width: 130px;
        }
        .diff-cell.up {
            color: var(--success);
        }
        .diff-cell.down {
            color: var(--danger);
        }
        
        .details-row {
            background-color: rgba(11, 15, 25, 0.5);
        }
        
        .details-row td {
            padding: 0;
            border-bottom: 1px solid var(--border);
        }
        
        .details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
            padding: 1.5rem 2rem;
            background-color: rgba(11, 15, 25, 0.4);
        }
        
        .detail-card {
            background-color: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 1.25rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .detail-card-title {
            font-size: 0.95rem;
            font-weight: 700;
            margin-bottom: 1rem;
            border-left: 3px solid var(--primary);
            padding-left: 0.5rem;
            color: #a5b4fc;
        }
        
        .metric-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .metric-row {
            margin-bottom: 0.25rem;
        }
        
        .metric-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            margin-bottom: 0.2rem;
        }
        
        .metric-name {
            font-weight: 500;
            color: var(--text-main);
        }
        
        .metric-values {
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        
        .metric-diff {
            font-weight: 600;
            font-size: 0.75rem;
            padding: 0.05rem 0.25rem;
            border-radius: 4px;
        }
        .metric-diff.up {
            color: var(--success);
            background-color: var(--success-glow);
        }
        .metric-diff.down {
            color: var(--danger);
            background-color: var(--danger-glow);
        }
        .metric-diff.neutral {
            color: var(--text-muted);
            background-color: rgba(255, 255, 255, 0.05);
        }
        
        .metric-bar-container {
            height: 4px;
            background-color: #1e293b;
            border-radius: 10px;
            overflow: hidden;
            width: 100%;
        }
        
        .metric-bar-fill {
            height: 100%;
            background-color: var(--primary);
            border-radius: 10px;
        }
        
        .moves-grid-details {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
        }
        
        .empty-state {
            text-align: center;
            color: var(--text-muted);
            padding: 1.5rem;
            font-size: 0.9rem;
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .header-grid {
                grid-template-columns: 1fr;
                text-align: center;
                gap: 1rem;
            }
            .vs-divider {
                margin: 0.5rem auto;
            }
            .highlights-section {
                grid-template-columns: 1fr;
            }
            .controls-bar {
                flex-direction: column;
                align-items: stretch;
            }
            th, td {
                padding: 0.75rem 0.5rem;
            }
            .rank-change, .pct-cell, .diff-cell {
                width: auto;
            }
        }
    </style>
</head>
<body>
    <div class="header-grid">
        <div class="tour-card">
            <span class="tour-label">Old Tournament</span>
            <h2 class="tour-title" id="old-title">-</h2>
            <div class="tour-meta" id="old-meta"></div>
        </div>
        <div class="vs-divider">VS</div>
        <div class="tour-card">
            <span class="tour-label">New Tournament</span>
            <h2 class="tour-title" id="new-title">-</h2>
            <div class="tour-meta" id="new-meta"></div>
        </div>
    </div>
    
    <div class="summary-grid">
        <div class="stat-card">
            <span class="stat-card-title">Player Count Change</span>
            <div class="stat-card-val" id="players-val">-</div>
        </div>
        <div class="stat-card">
            <span class="stat-card-title">Teams Analyzed Change</span>
            <div class="stat-card-val" id="teams-val">-</div>
        </div>
        <div class="stat-card">
            <span class="stat-card-title">Top Meta Winner</span>
            <div class="stat-card-val" id="top-winner-val" style="font-size: 1.4rem; color: var(--success);">-</div>
        </div>
        <div class="stat-card">
            <span class="stat-card-title">Top Meta Loser</span>
            <div class="stat-card-val" id="top-loser-val" style="font-size: 1.4rem; color: var(--danger);">-</div>
        </div>
    </div>
    
    <div class="highlights-section">
        <div class="highlight-card winners">
            <h3 class="highlight-title">📈 Top Meta Winners</h3>
            <div class="highlight-list" id="winners-list"></div>
        </div>
        
        <div class="highlight-card losers">
            <h3 class="highlight-title">📉 Top Meta Losers</h3>
            <div class="highlight-list" id="losers-list"></div>
        </div>
    </div>
    
    <div class="controls-bar">
        <div class="search-wrapper">
            <input type="text" class="search-input" id="search-input" placeholder="Search Pokémon...">
        </div>
        <div class="tabs-wrapper">
            <button class="tab-btn active" onclick="switchTab('all', this)">All</button>
            <button class="tab-btn" onclick="switchTab('winners', this)">Winners</button>
            <button class="tab-btn" onclick="switchTab('losers', this)">Losers</button>
            <button class="tab-btn" onclick="switchTab('new', this)">New</button>
            <button class="tab-btn" onclick="switchTab('dropped', this)">Dropped</button>
        </div>
    </div>
    
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Shift</th>
                    <th>Pokémon</th>
                    <th>Old Usage</th>
                    <th>New Usage</th>
                    <th>Delta</th>
                </tr>
            </thead>
            <tbody id="shifts-tbody"></tbody>
        </table>
    </div>

    <script>
        const data = {{JSON_DATA}};
        const pokes = data.pokemon_shifts;
        let activeTab = 'all';
        let searchQuery = '';
        
        // Render Header
        document.getElementById('old-title').innerText = data.old_tournament.name;
        document.getElementById('old-meta').innerHTML = `
            <span class="meta-badge">📅 ${data.old_tournament.date}</span>
            <span class="meta-badge">🏆 ${data.old_tournament.format}</span>
            <span class="meta-badge">👥 ${data.old_tournament.total_players} players</span>
            <span class="meta-badge">📊 ${data.old_tournament.teams_analyzed} teams</span>
        `;
        
        document.getElementById('new-title').innerText = data.new_tournament.name;
        document.getElementById('new-meta').innerHTML = `
            <span class="meta-badge">📅 ${data.new_tournament.date}</span>
            <span class="meta-badge">🏆 ${data.new_tournament.format}</span>
            <span class="meta-badge">👥 ${data.new_tournament.total_players} players</span>
            <span class="meta-badge">📊 ${data.new_tournament.teams_analyzed} teams</span>
        `;
        
        // Players difference
        const pDiff = data.new_tournament.total_players - data.old_tournament.total_players;
        const pDiffStr = pDiff > 0 ? `+${pDiff}` : pDiff;
        const pDiffClass = pDiff > 0 ? 'up' : (pDiff < 0 ? 'down' : 'neutral');
        document.getElementById('players-val').innerHTML = `
            ${data.new_tournament.total_players}
            <span class="stat-delta ${pDiffClass}">${pDiffStr}</span>
        `;
        
        // Teams difference
        const tDiff = data.new_tournament.teams_analyzed - data.old_tournament.teams_analyzed;
        const tDiffStr = tDiff > 0 ? `+${tDiff}` : tDiff;
        const tDiffClass = tDiff > 0 ? 'up' : (tDiff < 0 ? 'down' : 'neutral');
        document.getElementById('teams-val').innerHTML = `
            ${data.new_tournament.teams_analyzed}
            <span class="stat-delta ${tDiffClass}">${tDiffStr}</span>
        `;
        
        // Calculate Winners & Losers
        const validDiffs = pokes.filter(p => p.old_percentage > 0 || p.new_percentage > 0);
        
        const winners = [...validDiffs]
            .filter(p => p.percentage_diff > 0)
            .sort((a, b) => b.percentage_diff - a.percentage_diff)
            .slice(0, 5);
            
        const losers = [...validDiffs]
            .filter(p => p.percentage_diff < 0)
            .sort((a, b) => a.percentage_diff - b.percentage_diff)
            .slice(0, 5);
            
        // Render Stat Cards Tops
        if (winners.length > 0) {
            document.getElementById('top-winner-val').innerText = `${winners[0].name} (+${winners[0].percentage_diff.toFixed(1)}%)`;
        } else {
            document.getElementById('top-winner-val').innerText = 'N/A';
        }
        
        if (losers.length > 0) {
            document.getElementById('top-loser-val').innerText = `${losers[0].name} (${losers[0].percentage_diff.toFixed(1)}%)`;
        } else {
            document.getElementById('top-loser-val').innerText = 'N/A';
        }
        
        // Render Highlights Lists
        const winnersListEl = document.getElementById('winners-list');
        if (winners.length === 0) {
            winnersListEl.innerHTML = '<div class="empty-state">No significant rise</div>';
        } else {
            winnersListEl.innerHTML = winners.map(w => `
                <div class="highlight-item">
                    <span class="highlight-name">${w.name}</span>
                    <div class="highlight-val">
                        <span>${w.old_percentage.toFixed(1)}% → ${w.new_percentage.toFixed(1)}%</span>
                        <span class="pct-badge up">+${w.percentage_diff.toFixed(1)}%</span>
                    </div>
                </div>
            `).join('');
        }
        
        const losersListEl = document.getElementById('losers-list');
        if (losers.length === 0) {
            losersListEl.innerHTML = '<div class="empty-state">No significant fall</div>';
        } else {
            losersListEl.innerHTML = losers.map(l => `
                <div class="highlight-item">
                    <span class="highlight-name">${l.name}</span>
                    <div class="highlight-val">
                        <span>${l.old_percentage.toFixed(1)}% → ${l.new_percentage.toFixed(1)}%</span>
                        <span class="pct-badge down">${l.percentage_diff.toFixed(1)}%</span>
                    </div>
                </div>
            `).join('');
        }
        
        // Render Table
        function renderTable() {
            const tbody = document.getElementById('shifts-tbody');
            tbody.innerHTML = '';
            
            // Filter
            let filtered = pokes;
            
            // Filter by search query
            if (searchQuery) {
                const q = searchQuery.toLowerCase();
                filtered = filtered.filter(p => p.name.toLowerCase().includes(q));
            }
            
            // Filter by tab
            if (activeTab === 'winners') {
                filtered = filtered.filter(p => p.percentage_diff > 0);
            } else if (activeTab === 'losers') {
                filtered = filtered.filter(p => p.percentage_diff < 0);
            } else if (activeTab === 'new') {
                filtered = filtered.filter(p => p.old_rank === null && p.new_rank !== null);
            } else if (activeTab === 'dropped') {
                filtered = filtered.filter(p => p.old_rank !== null && p.new_rank === null);
            }
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No matching Pokémon found</td></tr>';
                return;
            }
            
            filtered.forEach(p => {
                const rowId = 'details-' + p.name.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
                
                // Rank change text & class
                let rcClass = 'neutral';
                let rcText = p.rank_change_str;
                
                if (p.rank_change_str.includes('▲')) {
                    rcClass = 'up';
                } else if (p.rank_change_str.includes('▼')) {
                    rcClass = 'down';
                } else if (p.rank_change_str.includes('New')) {
                    rcClass = 'new';
                    rcText = '🆕 New';
                } else if (p.rank_change_str.includes('Dropped')) {
                    rcClass = 'dropped';
                    rcText = '❌ Dropped';
                }
                
                const oldPctText = p.old_percentage > 0 ? `${p.old_percentage.toFixed(1)}%` : '—';
                const newPctText = p.new_percentage > 0 ? `${p.new_percentage.toFixed(1)}%` : '—';
                
                const diffVal = p.percentage_diff;
                const diffClass = diffVal > 0 ? 'up' : (diffVal < 0 ? 'down' : 'neutral');
                const diffText = diffVal > 0 ? `+${diffVal.toFixed(2)}%` : (diffVal < 0 ? `${diffVal.toFixed(2)}%` : '0.00%');
                
                const newRankText = p.new_rank !== null ? `#${p.new_rank}` : '—';
                
                const tr = document.createElement('tr');
                tr.id = 'trigger-' + rowId;
                tr.className = 'poke-row';
                tr.onclick = () => toggleRow(rowId, p);
                tr.innerHTML = `
                    <td class="rank-cell">${newRankText}</td>
                    <td class="rank-change ${rcClass}">${rcText}</td>
                    <td class="name-cell">${p.name}</td>
                    <td class="pct-cell">${oldPctText}</td>
                    <td class="pct-cell">${newPctText}</td>
                    <td class="diff-cell ${diffClass}">${diffText}</td>
                `;
                tbody.appendChild(tr);
                
                // Create details row
                const detailsTr = document.createElement('tr');
                detailsTr.id = rowId;
                detailsTr.className = 'details-row';
                detailsTr.style.display = 'none';
                detailsTr.innerHTML = `
                    <td colspan="6">
                        <div class="details-grid" id="grid-${rowId}">
                            <div class="empty-state">Loading details...</div>
                        </div>
                    </td>
                `;
                tbody.appendChild(detailsTr);
            });
        }
        
        function renderDetailSection(title, list) {
            if (!list || list.length === 0) {
                return `
                    <div class="detail-card">
                        <h4 class="detail-card-title">${title}</h4>
                        <div class="empty-state">N/A</div>
                    </div>
                `;
            }
            
            const active = list.filter(item => item.old_percentage > 0 || item.new_percentage > 0);
            if (active.length === 0) {
                return `
                    <div class="detail-card">
                        <h4 class="detail-card-title">${title}</h4>
                        <div class="empty-state">No shifts recorded</div>
                    </div>
                `;
            }
            
            const rowsHtml = active.slice(0, 8).map(item => {
                const diff = item.diff;
                const diffClass = diff > 0 ? 'up' : (diff < 0 ? 'down' : 'neutral');
                const diffStr = diff > 0 ? `+${diff.toFixed(1)}%` : (diff < 0 ? `${diff.toFixed(1)}%` : '0.0%');
                const diffText = diff !== 0 ? `<span class="metric-diff ${diffClass}">${diffStr}</span>` : '<span class="metric-diff neutral">▬</span>';
                
                return `
                    <div class="metric-row">
                        <div class="metric-info">
                            <span class="metric-name">${item.name}</span>
                            <span class="metric-values">${item.old_percentage.toFixed(1)}% → ${item.new_percentage.toFixed(1)}% ${diffText}</span>
                        </div>
                        <div class="metric-bar-container">
                            <div class="metric-bar-fill" style="width: ${item.new_percentage}%"></div>
                        </div>
                    </div>
                `;
            }).join('');
            
            return `
                <div class="detail-card">
                    <h4 class="detail-card-title">${title}</h4>
                    <div class="metric-list">${rowsHtml}</div>
                </div>
            `;
        }
        
        function renderDetailSectionWide(title, list) {
            if (!list || list.length === 0) {
                return `
                    <div class="detail-card">
                        <h4 class="detail-card-title">${title}</h4>
                        <div class="empty-state">N/A</div>
                    </div>
                `;
            }
            
            const active = list.filter(item => item.old_percentage > 0 || item.new_percentage > 0);
            if (active.length === 0) {
                return `
                    <div class="detail-card">
                        <h4 class="detail-card-title">${title}</h4>
                        <div class="empty-state">No shifts recorded</div>
                    </div>
                `;
            }
            
            const rowsHtml = active.slice(0, 12).map(item => {
                const diff = item.diff;
                const diffClass = diff > 0 ? 'up' : (diff < 0 ? 'down' : 'neutral');
                const diffStr = diff > 0 ? `+${diff.toFixed(1)}%` : (diff < 0 ? `${diff.toFixed(1)}%` : '0.0%');
                const diffText = diff !== 0 ? `<span class="metric-diff ${diffClass}">${diffStr}</span>` : '<span class="metric-diff neutral">▬</span>';
                
                return `
                    <div class="metric-row">
                        <div class="metric-info">
                            <span class="metric-name">${item.name}</span>
                            <span class="metric-values">${item.old_percentage.toFixed(1)}% → ${item.new_percentage.toFixed(1)}% ${diffText}</span>
                        </div>
                        <div class="metric-bar-container">
                            <div class="metric-bar-fill" style="width: ${item.new_percentage}%"></div>
                        </div>
                    </div>
                `;
            }).join('');
            
            return `
                <div class="detail-card">
                    <h4 class="detail-card-title">${title}</h4>
                    <div class="moves-grid-details">${rowsHtml}</div>
                </div>
            `;
        }
        
        function toggleRow(rowId, p) {
            const rowEl = document.getElementById(rowId);
            const triggerEl = document.getElementById('trigger-' + rowId);
            
            if (rowEl.style.display === 'none') {
                rowEl.style.display = 'table-row';
                triggerEl.classList.add('active');
                
                const gridEl = document.getElementById('grid-' + rowId);
                const itemsHtml = renderDetailSection("Popular Items", p.items);
                const abilitiesHtml = renderDetailSection("Popular Abilities", p.abilities);
                const terasHtml = renderDetailSection("Popular Tera Types", p.teras);
                const naturesHtml = renderDetailSection("Popular Natures", p.natures);
                const movesHtml = renderDetailSectionWide("Popular Moves", p.moves);
                
                gridEl.innerHTML = `
                    ${itemsHtml}
                    ${abilitiesHtml}
                    ${terasHtml}
                    ${naturesHtml}
                    <div style="grid-column: 1 / -1;">
                        ${movesHtml}
                    </div>
                `;
            } else {
                rowEl.style.display = 'none';
                triggerEl.classList.remove('active');
            }
        }
        
        function switchTab(tab, btn) {
            activeTab = tab;
            const btns = document.querySelectorAll('.tab-btn');
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            renderTable();
        }
        
        document.getElementById('search-input').oninput = (e) => {
            searchQuery = e.target.value;
            renderTable();
        };
        
        renderTable();
    </script>
</body>
</html>
"""
    html_content = html_template.replace("{{JSON_DATA}}", json_str)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)


def main():
    args = parse_args()
    
    # Xác định thư mục lưu kết quả mặc định
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = args.output_dir if args.output_dir else os.path.join(project_root, "results", "compare")
    
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
    
    os.makedirs(output_dir, exist_ok=True)
    md_filename = os.path.join(output_dir, f"{safe_old_name}_vs_{safe_new_name}_comparison.md")
    json_filename = os.path.join(output_dir, f"{safe_old_name}_vs_{safe_new_name}_comparison.json")
    
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
        
    # Ghi ra file HTML
    html_filename = os.path.join(output_dir, f"{safe_old_name}_vs_{safe_new_name}_comparison.html")
    write_html_comparison(comparison_results, html_filename)
        
    print(f"\n==================================================")
    print(f" THÀNH CÔNG: Đã tạo và lưu báo cáo so sánh tại:")
    print(f" -> Markdown: {os.path.abspath(md_filename)}")
    print(f" -> JSON: {os.path.abspath(json_filename)}")
    print(f" -> HTML: {os.path.abspath(html_filename)}")
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
