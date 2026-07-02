# Limitless VGC Top 8 Standings & PokePaste Generator

Một công cụ bằng Python tự động hóa 100% quy trình xử lý sau giải đấu Pokemon VGC trên Limitless. Công cụ sẽ tự động lấy danh sách Top 8 người chơi từ Limitless, tạo các liên kết PokePaste riêng biệt và kết xuất hình ảnh bảng xếp hạng Top 8 chuyên nghiệp chỉ bằng một dòng lệnh.

## Tính năng nổi bật

- **Zero-Dependency (Không cần cài đặt thư viện)**: Chỉ sử dụng các thư viện tích hợp sẵn của Python 3 (`urllib`, `json`, `re`, `ssl`, v.v.), chạy được ngay mà không cần `pip install`.
- **Tự động trích xuất ID**: Hỗ trợ nhập trực tiếp URL giải đấu của Limitless hoặc ID hex 24 ký tự.
- **Tự động tạo PokePaste**: Tự động dịch dữ liệu đội hình JSON trên Limitless sang định dạng Showdown và tải lên `pokepast.es`.
- **Ánh xạ tên thông minh**: Tự động chuyển đổi các dạng Pokemon vùng miền (ví dụ: `Hisuian Arcanine` -> `Arcanine-Hisui`, `Galarian Slowbro` -> `Slowbro-Galar`) và các dạng đặc biệt (ví dụ: `Wash Rotom` -> `Rotom-wash`, `Eternal Flower Floette` -> `Floette-eternal`) để tránh lỗi khi tạo ảnh.
- **Kết xuất hình ảnh tự động**: Gửi dữ liệu Top 8 đến API của `generator.joaoabel.pt` để tạo và lưu hình ảnh bảng xếp hạng chất lượng cao về máy.

## Cấu trúc dự án

- `src/`: Thư mục chứa các tệp mã nguồn Python chính.
  - `generate_top8.py`: Script tự động tạo ảnh bảng xếp hạng và PokePaste cho Top 8 người chơi.
  - `fetch_usage.py`: Script tự động thu thập và phân tích chỉ số sử dụng (Usage Statistics) của tất cả người chơi.
  - `compare_usage.py`: Script tự động so sánh biến động metagame và cách xây dựng giữa các tuần giải đấu.
  - `compare_season.py`: Script tự động phân tích và trực quan hóa xu hướng metagame cả mùa giải qua chuỗi các giải đấu.
- `data/`: Thư mục chứa từ điển ánh xạ chuẩn hóa tên.
  - `pokemon_name_mapping.json`: Từ điển ánh xạ tên Pokemon.
  - `item_name_mapping.json`: Từ điển ánh xạ tên vật phẩm.
- `docs/`: Thư mục chứa tài liệu hướng dẫn và kế hoạch phát triển.
  - `walkthrough.md`: Hướng dẫn vận hành chi tiết và lịch sử kiểm thử.
  - `implementation_plan.md`: Kế hoạch triển khai dự án.
- `README.md`: Tài liệu hướng dẫn sử dụng tổng quan này.

## Yêu cầu hệ thống

- Đã cài đặt **Python 3.x** trên máy.

## Hướng dẫn sử dụng

### 1. Tự động kết xuất Top 8 (src/generate_top8.py)

Mở Terminal hoặc Command Prompt tại thư mục dự án và chạy:

```bash
python3 src/generate_top8.py "<URL hoặc ID giải đấu trên Limitless>"
```

#### Ví dụ:
```bash
python3 src/generate_top8.py "https://play.limitlesstcg.com/tournament/6a141fe98c163b8097996cc4/standings"
```

#### Kết quả đầu ra:
- **Ảnh bảng xếp hạng**: File ảnh `.png` (ví dụ: `Alpensee_Tour_top8.png`) được lưu trực tiếp tại thư mục hiện tại.
- **Báo cáo trên Terminal**: In bảng Markdown tóm tắt thứ hạng, tên, quốc gia, kết quả trận đấu, và link PokePaste của từng người chơi trong Top 8.

---

### 2. Phân tích chỉ số sử dụng (src/fetch_usage.py)

Script này giúp thống kê tần suất xuất hiện (Usage rate) của Pokemon, vật phẩm (Items), đặc tính (Abilities), hệ Tera (Tera Types), tính cách (Natures), và các chiêu thức (Moves) của giải đấu.

#### Cách chạy:
```bash
python3 src/fetch_usage.py "<URL hoặc ID giải đấu>" [tùy chọn]
```

#### Các tham số tùy chọn:
- `-k`, `--key`: Cung cấp **Limitless API Key** để truy cập các giải đấu riêng tư (Private tournaments). Bạn cũng có thể thiết lập biến môi trường `LIMITLESS_API_KEY`.
- `-o`, `--output-dir`: Thư mục lưu file báo cáo kết quả (mặc định là thư mục hiện tại `.`).
- `-l`, `--limit`: Số lượng Pokemon đứng đầu hiển thị chi tiết build (mặc định là `20`, truyền `-1` để xem tất cả).

#### Ví dụ:
- Phân tích giải đấu công khai (Public):
  ```bash
  python3 src/fetch_usage.py "https://play.limitlesstcg.com/tournament/6a141fe98c163b8097996cc4/standings"
  ```
- Phân tích giải đấu riêng tư (Private) bằng API Key:
  ```bash
  python3 src/fetch_usage.py "https://play.limitlesstcg.com/tournament/private_tour_id/standings" -k "YOUR_LIMITLESS_API_KEY"
  ```

#### Kết quả đầu ra:
- **Báo cáo chi tiết Markdown**: File `.md` (ví dụ: `Alpensee_Tour_usage.md`) hiển thị bảng xếp hạng tổng và bảng chi tiết xây dựng build cho từng Pokemon (Vật phẩm, Đặc tính, Hệ Tera, Chiêu thức, Tính cách).
- **Dữ liệu JSON**: File `.json` chứa toàn bộ dữ liệu cấu trúc sạch để dễ dàng tích hợp hoặc xử lý tiếp.
- **Tóm tắt trên Terminal**: Hiển thị Top 10 Pokemon được sử dụng nhiều nhất.

---

### 3. So sánh biến động metagame (src/compare_usage.py)

Script này giúp so sánh dữ liệu chỉ số sử dụng giữa 2 giải đấu (hoặc tuần thi đấu trước và sau) thông qua hai tệp JSON được tạo ra bởi `fetch_usage.py`. Nó sẽ tính toán tự động chênh lệch phần trăm sử dụng, dịch chuyển thứ hạng, biến động vật phẩm, đặc tính, Tera type và chiêu thức sử dụng trên từng Pokémon.

#### Cách chạy:
```bash
python3 src/compare_usage.py <đường_dẫn_json_cũ> <đường_dẫn_json_mới> [tùy_chọn]
```

#### Các tham số tùy chọn:
- `-o`, `--output-dir`: Thư mục lưu báo cáo kết quả (mặc định: thư mục hiện tại `.`).
- `-l`, `--limit`: Số lượng Pokémon hàng đầu phân tích chi tiết biến động build (mặc định: `10`, truyền `-1` để phân tích tất cả).

#### Ví dụ:
```bash
python3 src/compare_usage.py "Alpensee_Tour_60_usage.json" "Alpensee_Tour_62_usage.json"
```

#### Kết quả đầu ra:
- **Báo cáo dịch chuyển meta (Markdown)**: File `.md` (ví dụ: `Alpensee_Tour_60_vs_Alpensee_Tour_62_comparison.md`) hiển thị bảng biến động thứ hạng trực quan (`▲`, `▼`, `▬`, `New`, `Dropped`) và chi tiết sự tăng giảm sử dụng vật phẩm/chiêu thức cụ thể.
- **Dữ liệu so sánh JSON**: File `.json` chứa thông tin so sánh hoàn chỉnh dạng cấu trúc.
- **Tóm tắt trên Terminal**: In ra các Pokémon tăng trưởng (Winners) và suy giảm (Losers) mạnh nhất.

---

### 3. Phân tích xu hướng cả mùa giải (src/compare_season.py)

Mở Terminal hoặc Command Prompt tại thư mục dự án và chạy:

```bash
python3 src/compare_season.py <Đường dẫn các tệp JSON giải đấu...> --name "<Tên Mùa Giải>"
```

#### Ví dụ:
```bash
python3 src/compare_season.py "results/usage/tour1_usage.json" "results/usage/tour2_usage.json" --name "VGC 2026 Summer Season"
```

#### Kết quả đầu ra:
- **Bản đồ tương tác Heatmap & Biểu đồ xu hướng (HTML)**: Lưu tại `results/season/[tên_mùa_giải]_season.html` với đầy đủ các tab timeline biến động sử dụng (vạch phân cách format shift), ma trận heatmap sử dụng và bảng phân tích winners/losers.
- **Biểu đồ Item cho từng Pokémon**: Bảng Heatmap hỗ trợ click vào dòng bất kỳ để mở rộng xem biểu đồ hình cột chi tiết về các vật phẩm được sử dụng nhiều nhất cho Pokémon đó trong suốt mùa giải.
- **Dữ liệu Season JSON**: Lưu dữ liệu cấu trúc đầy đủ tại `results/season/[tên_mùa_giải]_season.json`.

---

### 4. Giao diện điều khiển đồ họa (Local Desktop App - src/app.py)

Đây là giao diện điều khiển đồ họa chạy local trên trình duyệt của bạn (Zero-Dependency), giúp bạn thực hiện tất cả các thao tác trên một cách dễ dàng, trực quan mà không cần gõ lệnh Terminal:
- **Giao diện Dashboard cao cấp**: Thiết kế Premium Dark Mode, hiển thị trực quan các kết quả phân tích.
- **Hỗ trợ đa dạng đầu vào**: Nhận diện thông minh cả Tournament ID 24 ký tự hex lẫn link URL giải đấu Limitless trực tiếp.
- **Console Log thời gian thực**: Theo dõi từng bước phân tích ngay trên màn hình (Đang tải standings, Đang lấy đội hình, v.v.).
- **Quản lý lịch sử**: Xem và truy cập nhanh danh sách tất cả các báo cáo đã tạo trước đó.
- **Check Update tự động**: Kết nối với GitHub Releases API để hiển thị banner thông báo cập nhật ngay lập tức khi bạn phát hành phiên bản mới trên GitHub.

#### Cách chạy:
```bash
python3 src/app.py
```
Ứng dụng sẽ tự động khởi chạy một web server mini local tại địa chỉ `http://127.0.0.1:5000` và tự động mở tab trình duyệt mặc định của bạn.

## Nhật ký cập nhật (Changelog)

### v2.0.1-beta (02/07/2026)
- **Tính năng Phân tích xu hướng cả mùa giải (`src/compare_season.py`)**:
  - So sánh metagame qua chuỗi các giải đấu trong mùa giải.
  - Vẽ biểu đồ timeline bằng Chart.js cho Top 10 Pokémon, hỗ trợ vẽ vạch phân cách chuyển đổi thể thức (format shift).
  - Xuất bảng Heatmap Matrix tỉ lệ sử dụng qua các giải đấu với màu sắc phân cấp.
  - Tích hợp biểu đồ cột ngang cho Top 5 Vật phẩm (Items) sử dụng của từng Pokémon dạng expandable row.
  - Thêm tab **Season Analyzer** trên thanh Menu của ứng dụng Local App, hỗ trợ chọn giải đấu bằng checkbox.

### v2.0.0-beta (26/06/2026)
- **Giao diện điều khiển đồ họa Local Desktop (`src/app.py` & `src/templates/index.html`)**:
  - Phát triển ứng dụng GUI cục bộ dạng Local Web App với zero-dependency (chỉ sử dụng thư viện chuẩn của Python).
  - Tích hợp Server-Sent Events (SSE) để truyền phát console log của các script chạy ngầm lên giao diện Web thời gian thực.
  - Hỗ trợ ghi nhớ Limitless API Key trong localStorage của trình duyệt.
  - Tự động gọi GitHub Releases API để thông báo cập nhật cho người dùng nếu phát hiện bản phát hành mới.
- **Đảo ngược bảng tổng hợp Top 12 Pokémon (Transposed summary table)**:
  - Cập nhật cách bố trí của bảng tóm tắt Top 12 trong HTML: chuyển Pokémon thành dòng (dọc) và các metric (Item, Move, Ability, Teammates) thành cột (ngang) giúp dễ theo dõi và tương thích màn hình tốt hơn.

### v1.2.0 (18/06/2026)
- **Tính năng so sánh metagame (`compare_usage.py`)**:
  - Hỗ trợ so sánh tự động dịch chuyển thứ hạng (Rank shifts) và tỷ lệ sử dụng (Usage rate) giữa 2 tuần giải đấu/tệp JSON.
  - Phân tích chi tiết sự thay đổi về Vật phẩm (Items), Đặc tính (Abilities), Chiêu thức (Moves), Hệ Tera, và Tính cách (Natures) cụ thể trên từng Pokémon theo dạng so sánh `Cũ -> Mới (Chênh lệch)`.
  - Xuất báo cáo trực quan dưới dạng bảng Markdown (`.md`) và tệp JSON so sánh cấu trúc sạch.
- **Cập nhật danh sách Mega hỗ trợ**: Bổ sung cấu hình ánh xạ cho Scolipede Mega, Scrafty Mega, Pyroar Mega, và Dragalge Mega. Mở rộng danh sách fallback an toàn cho các dạng Mega chưa được Generator hỗ trợ (Mega Raichu X/Y, Mega Staraptor, Mega Eelektross, Mega Malamar, Mega Barbaracle, Mega Falinks).

### v1.1.0 (18/06/2026)
- **Hỗ trợ Regulation M-B**: Cập nhật ánh xạ thể thức thi đấu mới Regulation M-B vào `format_map`.
- **Tính năng phân tích Usage Statistics (`fetch_usage.py`)**:
  - Hỗ trợ thu thập và thống kê số lần xuất hiện của từng Pokémon trong giải đấu.
  - Phân tích chi tiết số lần sử dụng của các Vật phẩm (Items), Đặc tính (Abilities), Chiêu thức (Moves), Hệ Tera, và Tính cách (Natures) trên từng Pokémon.
  - Xuất báo cáo trực quan dưới dạng Markdown (`.md`) và dữ liệu cấu trúc sạch (`.json`).
  - Hỗ trợ API Key để lấy dữ liệu từ các giải đấu riêng tư (Private Tournaments).
- **Tự động nhận diện Mega Pokémon**: Tự động quét vật phẩm để phát hiện Pokémon tiến hóa Mega, chọn sprite Mega thích hợp cho Generator API.
- **Cơ chế Fallback chống lỗi**: Tự động chuyển Pokémon Mega về dạng thường nếu Generator API không hỗ trợ sprite Mega đó (ví dụ: Mega Staraptor, Mega Raichu) để tránh lỗi crash HTTP 500.

## Đóng góp ý kiến

Nếu bạn gặp bất kỳ vấn đề nào liên quan đến việc ánh xạ tên Pokemon hoặc lỗi kết nối API, vui lòng gửi phản hồi hoặc tự cập nhật trực tiếp vào hai file `data/pokemon_name_mapping.json` và `data/item_name_mapping.json`.

---
*Dự án sử dụng API công khai của [Limitless TCG/VGC](https://play.limitlesstcg.com) và dịch vụ tạo ảnh của [VGC Standings Generator](https://generator.joaoabel.pt) của tác giả João Costa.*
