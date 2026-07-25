# Movie Analytics with MongoDB

Đồ án quản lý và phân tích dữ liệu phim bằng MongoDB, sử dụng thiết kế query-first.

## Dataset

Dataset đầu vào được tải từ [The Movies Dataset trên Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset). Sau khi tải và giải nén, đặt bốn file sau vào thư mục `dataset/` để pipeline ETL tổng hợp dữ liệu vào MongoDB:

- `dataset/movies_metadata.csv`
- `dataset/credits.csv`
- `dataset/ratings_small.csv`
- `dataset/links_small.csv`

`ratings.csv` không được sử dụng. `links_small.csv` ánh xạ MovieLens ID trong ratings sang TMDB ID trong metadata. Thông tin nguồn, giấy phép và citation đầy đủ nằm tại [`dataset/README.md`](dataset/README.md).

### Dữ liệu synthetic

Trong phạm vi đồ án, toàn bộ dữ liệu được tổng hợp vào MongoDB được xem là dữ liệu synthetic phục vụ học tập, mô phỏng và phân tích; dữ liệu này không đại diện cho một hệ thống nghiệp vụ đang vận hành.

Phim, credits, links và ratings được ETL từ các file tải trên Kaggle. Riêng thông tin nhân khẩu học không có trong dữ liệu MovieLens nhỏ, nên hệ thống sinh xác định `age`, `ageGroup` và `country` cho 671 users bằng seed mặc định `2026`.

## Yêu cầu

- Python 3.11 trở lên
- MongoDB 7 hoặc 8
- `mongosh`
- GNU Make

Kiểm tra các công cụ đã được cài đặt:

```bash
python --version
mongod --version
mongosh --version
make --version
```

## Cài đặt

### 1. Cài Python dependencies

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Cấu hình môi trường

Tạo file cấu hình nếu cần thay đổi giá trị mặc định:

```bash
cp .env.example .env
```

`Makefile` tự động nạp `.env`. Nếu không tạo file này, dự án vẫn sử dụng MongoDB mặc định tại `mongodb://localhost:27017/movie_analytics` và các giá trị được khai báo trong `Makefile`.

Các tham số chính:

| Biến | Mặc định | Mục đích |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` | Địa chỉ MongoDB server |
| `MONGODB_DATABASE` | `movie_analytics` | Tên database |
| `DATASET_DIR` | `dataset` | Thư mục chứa CSV |
| `ETL_BATCH_SIZE` | `5000` | Kích thước batch ETL |
| `USER_SEED` | `2026` | Seed sinh demographics synthetic |

### 3. Khởi động MongoDB

Đảm bảo MongoDB server đang chạy trước khi import. Kiểm tra kết nối bằng:

```bash
mongosh "mongodb://localhost:27017" --eval "db.runCommand({ping: 1})"
```

### 4. Khởi tạo dữ liệu

Sau khi bốn file CSV cần thiết đã có trong `dataset/`:

```bash
make init
```

Lệnh này lần lượt chạy setup database, ETL và rebuild các collection dẫn xuất. Có thể xem toàn bộ lệnh hỗ trợ bằng:

```bash
make help
```

### MongoDB for VS Code (tùy chọn)

Cài extension **MongoDB for VS Code**, kết nối tới `mongodb://localhost:27017`, sau đó mở các file `scripts/queries/*.mongodb.js`. Định dạng MongoDB Playground cung cấp IntelliSense cho MongoDB Shell API và cho phép chạy query trực tiếp trong VS Code.

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

ETL dùng upsert nên có thể chạy lại. Dữ liệu nhân khẩu học của 671 users được sinh xác định với seed `2026`.

## Chạy truy vấn

```bash
make query-1
make query-2 PERSON_NAME="Christopher Nolan"
make query-3 LIMIT=10
make query-4 MIN_RATINGS=20
make query-5 GENRE_NAME="Action"
make query-6
make query-test
```

Chạy `make help` để xem nhanh danh sách lệnh. Các tham số trên lệnh được ưu tiên hơn giá trị trong `.env` và giá trị mặc định.

Các query in kết quả thành bảng trong terminal. Q3 trả hai bảng riêng cho Actor và Director. Q4 dùng ngưỡng mặc định 20 ratings. Q5 trả báo cáo phân cấp. Q6 trả bảng pivot cho năm thể loại doanh thu cao nhất và phân biệt `N/A (no movies)` với `N/A (missing budget)`.

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
