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

Các script đọc biến môi trường trực tiếp từ shell; file `.env` là mẫu cấu hình và không tự động được nạp.

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
export MONGODB_URI=mongodb://localhost:27017
export MONGODB_DATABASE=movie_analytics

.venv/bin/python scripts/setup/setup_database.py
.venv/bin/python scripts/etl/import_data.py
mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/aggregate/rebuild_derived.js
```

ETL dùng upsert nên có thể chạy lại. Dữ liệu nhân khẩu học của 671 users được sinh xác định với seed `2026` và được đánh dấu `isSynthetic: true`.

## Chạy truy vấn

```bash
mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_01_top_action_movies.js
PERSON_NAME="Christopher Nolan" mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_02_person_career.js
mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_03_most_active_people.js
MIN_RATINGS=20 mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_04_top_genre_by_demographic.js
GENRE_NAME="Action" mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_05_country_age_report.js
mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_06_company_investment.js
```

Q3 trả hai bảng riêng cho Actor và Director. Q4 dùng ngưỡng mặc định 20 ratings. Q5 trả báo cáo phân cấp và Q6 trả đối tượng pivot kèm danh sách năm thể loại doanh thu cao nhất.

## Đo hiệu năng

```bash
mongosh "$MONGODB_URI/$MONGODB_DATABASE" --quiet scripts/validation/benchmark_queries.js
```

Kết quả và phân tích index được ghi tại `docs/performance-report.md`.

## Thứ tự dữ liệu

1. Collection danh mục và `movies`
2. `people` và `personCredits`
3. Users giả lập
4. Ratings hợp lệ
5. Thống kê và collection dẫn xuất

Các bản ghi bị loại được lưu trong `etlRejects`, kèm nguồn, dòng và lý do.
