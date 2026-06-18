# Limitless VGC Top 8 Standings & PokePaste Generator

Một công cụ bằng Python tự động hóa 100% quy trình xử lý sau giải đấu Pokemon VGC trên Limitless. Công cụ sẽ tự động lấy danh sách Top 8 người chơi từ Limitless, tạo các liên kết PokePaste riêng biệt và kết xuất hình ảnh bảng xếp hạng Top 8 chuyên nghiệp chỉ bằng một dòng lệnh.

## Tính năng nổi bật

- **Zero-Dependency (Không cần cài đặt thư viện)**: Chỉ sử dụng các thư viện tích hợp sẵn của Python 3 (`urllib`, `json`, `re`, `ssl`, v.v.), chạy được ngay mà không cần `pip install`.
- **Tự động trích xuất ID**: Hỗ trợ nhập trực tiếp URL giải đấu của Limitless hoặc ID hex 24 ký tự.
- **Tự động tạo PokePaste**: Tự động dịch dữ liệu đội hình JSON trên Limitless sang định dạng Showdown và tải lên `pokepast.es`.
- **Ánh xạ tên thông minh**: Tự động chuyển đổi các dạng Pokemon vùng miền (ví dụ: `Hisuian Arcanine` -> `Arcanine-Hisui`, `Galarian Slowbro` -> `Slowbro-Galar`) và các dạng đặc biệt (ví dụ: `Wash Rotom` -> `Rotom-wash`, `Eternal Flower Floette` -> `Floette-eternal`) để tránh lỗi khi tạo ảnh.
- **Kết xuất hình ảnh tự động**: Gửi dữ liệu Top 8 đến API của `generator.joaoabel.pt` để tạo và lưu hình ảnh bảng xếp hạng chất lượng cao về máy.

## Cấu trúc dự án

- `generate_top8.py`: Script tự động tạo bảng xếp hạng và PokePaste cho Top 8 người chơi.
- `fetch_usage.py`: Script tự động thu thập và phân tích chỉ số sử dụng (Usage Statistics) của tất cả người chơi trong giải đấu (hỗ trợ cả giải đấu Public và Private).
- `pokemon_name_mapping.json`: Dữ liệu ánh xạ tên Pokemon tương thích API generator và chuẩn hóa tên.
- `item_name_mapping.json`: Dữ liệu ánh xạ tên vật phẩm tương thích API generator và chuẩn hóa tên.
- `README.md`: Hướng dẫn sử dụng này.

## Yêu cầu hệ thống

- Đã cài đặt **Python 3.x** trên máy.

## Hướng dẫn sử dụng

### 1. Tự động kết xuất Top 8 (generate_top8.py)

Mở Terminal hoặc Command Prompt tại thư mục dự án và chạy:

```bash
python3 generate_top8.py "<URL hoặc ID giải đấu trên Limitless>"
```

#### Ví dụ:
```bash
python3 generate_top8.py "https://play.limitlesstcg.com/tournament/6a141fe98c163b8097996cc4/standings"
```

#### Kết quả đầu ra:
- **Ảnh bảng xếp hạng**: File ảnh `.png` (ví dụ: `Alpensee_Tour_top8.png`) được lưu trực tiếp tại thư mục hiện tại.
- **Báo cáo trên Terminal**: In bảng Markdown tóm tắt thứ hạng, tên, quốc gia, kết quả trận đấu, và link PokePaste của từng người chơi trong Top 8.

---

### 2. Phân tích chỉ số sử dụng (fetch_usage.py)

Script này giúp thống kê tần suất xuất hiện (Usage rate) của Pokemon, vật phẩm (Items), đặc tính (Abilities), hệ Tera (Tera Types), tính cách (Natures), và các chiêu thức (Moves) của giải đấu.

#### Cách chạy:
```bash
python3 fetch_usage.py "<URL hoặc ID giải đấu>" [tùy chọn]
```

#### Các tham số tùy chọn:
- `-k`, `--key`: Cung cấp **Limitless API Key** để truy cập các giải đấu riêng tư (Private tournaments). Bạn cũng có thể thiết lập biến môi trường `LIMITLESS_API_KEY`.
- `-o`, `--output-dir`: Thư mục lưu file báo cáo kết quả (mặc định là thư mục hiện tại `.`).
- `-l`, `--limit`: Số lượng Pokemon đứng đầu hiển thị chi tiết build (mặc định là `20`, truyền `-1` để xem tất cả).

#### Ví dụ:
- Phân tích giải đấu công khai (Public):
  ```bash
  python3 fetch_usage.py "https://play.limitlesstcg.com/tournament/6a141fe98c163b8097996cc4/standings"
  ```
- Phân tích giải đấu riêng tư (Private) bằng API Key:
  ```bash
  python3 fetch_usage.py "https://play.limitlesstcg.com/tournament/private_tour_id/standings" -k "YOUR_LIMITLESS_API_KEY"
  ```

#### Kết quả đầu ra:
- **Báo cáo chi tiết Markdown**: File `.md` (ví dụ: `Alpensee_Tour_usage.md`) hiển thị bảng xếp hạng tổng và bảng chi tiết xây dựng build cho từng Pokemon (Vật phẩm, Đặc tính, Hệ Tera, Chiêu thức, Tính cách).
- **Dữ liệu JSON**: File `.json` chứa toàn bộ dữ liệu cấu trúc sạch để dễ dàng tích hợp hoặc xử lý tiếp.
- **Tóm tắt trên Terminal**: Hiển thị Top 10 Pokemon được sử dụng nhiều nhất.

## Nhật ký cập nhật (Changelog)

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

Nếu bạn gặp bất kỳ vấn đề nào liên quan đến việc ánh xạ tên Pokemon hoặc lỗi kết nối API, vui lòng gửi phản hồi hoặc tự cập nhật trực tiếp vào hai file `pokemon_name_mapping.json` và `item_name_mapping.json`.

---
*Dự án sử dụng API công khai của [Limitless TCG/VGC](https://play.limitlesstcg.com) và dịch vụ tạo ảnh của [VGC Standings Generator](https://generator.joaoabel.pt) của tác giả João Costa.*
