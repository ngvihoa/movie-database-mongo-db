# Movie Analytics with MongoDB

Đồ án quản lý và phân tích dữ liệu phim bằng MongoDB, sử dụng thiết kế query-first.

## Dataset

Pipeline sử dụng bốn file:

- `dataset/movies_metadata.csv`
- `dataset/credits.csv`
- `dataset/ratings_small.csv`
- `dataset/links_small.csv`

`ratings.csv` không được sử dụng. `links_small.csv` ánh xạ MovieLens ID trong ratings sang TMDB ID trong metadata.

## Yêu cầu

- Python 3.11 trở lên
- MongoDB 7 hoặc 8
- `mongosh`

## Cài đặt

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

`Makefile` tự động nạp `.env` nếu file tồn tại. Nếu không có `.env`, các lệnh `make` sử dụng cấu hình mặc định trong `.env.example`, gồm MongoDB tại `mongodb://localhost:27017/movie_analytics`.

## Kiểm định dataset

Script này chỉ dùng Python chuẩn, không cần MongoDB:

```bash
python scripts/validation/inspect_dataset.py
```

Xuất báo cáo JSON:

```bash
python scripts/validation/inspect_dataset.py --output docs/data-quality-report.json
```

Kết quả chuẩn hiện tại là 100.004 ratings đầu vào, 99.810 ratings hợp lệ và 194 ratings bị loại do không ánh xạ được sang metadata.

## Khởi tạo và import

```bash
make init
```

Có thể chạy riêng từng bước bằng `make setup`, `make import` và `make rebuild`.

ETL dùng upsert nên có thể chạy lại. Dữ liệu nhân khẩu học của 671 users được sinh xác định với seed `2026` và được đánh dấu `isSynthetic: true`.

## Chạy truy vấn

```bash
make query-1
make query-2 PERSON_NAME="Christopher Nolan"
make query-3 LIMIT=10
make query-4 MIN_RATINGS=20
make query-5 GENRE_NAME="Action"
make query-6
```

Chạy `make help` để xem nhanh danh sách lệnh. Các tham số trên lệnh được ưu tiên hơn giá trị trong `.env` và giá trị mặc định.

Q3 trả hai bảng riêng cho Actor và Director. Q4 dùng ngưỡng mặc định 20 ratings. Q5 trả báo cáo phân cấp và Q6 trả đối tượng pivot kèm danh sách năm thể loại doanh thu cao nhất.

## Đo hiệu năng

```bash
make benchmark
```

Kết quả và phân tích index được ghi tại `docs/performance-report.md`.

## Thứ tự dữ liệu

1. Collection danh mục và `movies`
2. `people` và `personCredits`
3. Users giả lập
4. Ratings hợp lệ
5. Thống kê và collection dẫn xuất

Các bản ghi bị loại được lưu trong `etlRejects`, kèm nguồn, dòng và lý do.
