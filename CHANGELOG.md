# Changelog

Tất cả các thay đổi lớn đối với dự án **VGC-Analytics** sẽ được ghi nhận tại tài liệu này.

---

## [v2.0.1-beta] - 2026-07-02

### Added
- **Phân tích xu hướng cả mùa giải (Season Trend Analyzer)**:
  - Thêm script [src/compare_season.py](file:///Users/huy/Code/test/private/src/compare_season.py) để phân tích xu hướng metagame qua chuỗi các giải đấu trong một mùa giải.
  - Vẽ biểu đồ timeline xu hướng sử dụng của Top 10 Pokémon bằng Chart.js.
  - Tự động vẽ vạch kẻ phân cách khi phát hiện sự chuyển đổi thể thức thi đấu (mid-season format shifts), kèm theo bảng phân tích các Pokémon thắng/thua trong đợt chuyển đổi (Winners & Losers).
  - Tích hợp bảng ma trận Heatmap Matrix hiển thị tỉ lệ sử dụng qua các giải đấu với màu sắc phân cấp rực rỡ và trực quan.
  - Bổ sung biểu đồ cột ngang thể hiện tỉ lệ sử dụng Top 5 Vật phẩm (Items) của từng Pokémon dưới dạng expandable row (nhấn vào dòng Pokémon để xem chi tiết).
- **Cập nhật Giao diện Local App**:
  - Tích hợp tab **Season Analyzer** trên thanh Menu của [src/templates/index.html](file:///Users/huy/Code/test/private/src/templates/index.html).
  - Tự động quét và hiển thị danh sách checkbox các giải đấu JSON đã lưu để người dùng lựa chọn so sánh.

---

## [v2.0.0-beta] - 2026-06-26

### Added
- **Giao diện đồ họa cục bộ (Local Desktop App)**:
  - File chạy chính [src/app.py](file:///Users/huy/Code/test/private/src/app.py) và giao diện [src/templates/index.html](file:///Users/huy/Code/test/private/src/templates/index.html).
  - Khởi chạy một local web server gọn nhẹ không phụ thuộc bất kỳ thư viện bên thứ 3 nào (Zero-Dependency).
  - Tự động mở trình duyệt mặc định khi chạy ứng dụng.
  - Sử dụng Server-Sent Events (SSE) để truyền phát output console log từ quá trình thực thi script Python lên giao diện Web thời gian thực.
  - Giao diện Premium Dark Mode hiện đại, sử dụng font chữ Outfit, hỗ trợ lưu trữ API Key trong `localStorage` của trình duyệt.
  - Cơ chế tự động check cập nhật phiên bản mới bằng cách gọi API của GitHub Releases trên startup.
  - Hộp nhập giải đấu chấp nhận cả ID giải đấu 24 ký tự và đường dẫn URL đầy đủ.
  - Danh sách lịch sử hiển thị trực quan các báo cáo đã tạo để xem nhanh.

### Changed
- **Đảo ngược bảng tổng hợp Metagame Top 12**:
  - Chuyển giao diện cột của Top 12 Pokémon thành hàng dọc, và đưa các metric (Vật phẩm, chiêu thức, đặc tính, đồng đội) thành cột ngang. Điều này giúp tối ưu hóa không gian hiển thị, loại bỏ thanh cuộn khóa cột cố định và tăng tính tương thích hiển thị trên nhiều màn hình.

---

## [v1.2.0] - 2026-06-18

### Added
- **So sánh metagame (`compare_usage.py`)**:
  - So sánh tự động dịch chuyển thứ hạng (Rank shifts) và tỷ lệ sử dụng (Usage rate) giữa 2 tuần giải đấu/tệp JSON.
  - Phân tích chi tiết sự thay đổi về Vật phẩm (Items), Đặc tính (Abilities), Chiêu thức (Moves), Hệ Tera, và Tính cách (Natures) cụ thể trên từng Pokémon theo dạng so sánh `Cũ -> Mới (Chênh lệch)`.
  - Xuất báo cáo dưới dạng Markdown (`.md`) và tệp JSON so sánh cấu trúc sạch.
- **Ánh xạ Pokemon Mega mới**: Scolipede Mega, Scrafty Mega, Pyroar Mega, và Dragalge Mega.
- **Safe Fallback**: Tự động chuyển đổi dạng Mega về thường cho các dạng Mega chưa được generator hỗ trợ (Mega Raichu X/Y, Mega Staraptor, Mega Eelektross, Mega Malamar, Mega Barbaracle, Mega Falinks).

---

## [v1.1.0] - 2026-06-18

### Added
- **Thống kê Usage Statistics (`fetch_usage.py`)**:
  - Thống kê tỷ lệ sử dụng của Pokémon, Vật phẩm, Đặc tính, Chiêu thức, Tera, Tính cách.
  - Hỗ trợ API Key để lấy dữ liệu giải đấu riêng tư (Private Tournaments).
- **Hỗ trợ Regulation M-B**: Bổ sung Regulation M-B vào hệ thống format.
- **Tự động nhận diện Mega Pokémon** dựa trên vật phẩm trang bị.

---

## [v1.0.0] - 2026-06-04

### Added
- **Khởi tạo dự án**:
  - Tự động lấy danh sách Top 8 người chơi từ giải đấu Limitless.
  - Tự động tạo Showdown text và tải lên PokePaste (`pokepast.es`).
  - Gửi dữ liệu vẽ ảnh bảng xếp hạng Top 8 chuyên nghiệp.
