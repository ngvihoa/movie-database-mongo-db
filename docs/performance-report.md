# Báo cáo hiệu năng truy vấn MongoDB

## 1. Phạm vi đo

Kết quả được đo bằng `scripts/validation/benchmark_queries.js` trên database `movie_analytics` sau khi chạy `make setup` và `make rebuild`. Kiến trúc hiện tại có 8 collection nghiệp vụ; Q4 và Q6 tổng hợp trực tiếp từ dữ liệu nghiệp vụ, không dùng collection materialized.

Thời gian là kết quả của một lần chạy tại môi trường phát triển và chỉ dùng để kiểm tra kế hoạch thực thi, không phải cam kết hiệu năng sản xuất.

## 2. Kết quả hiện tại

| Truy vấn | Collection | Kết quả | Thời gian thực thi | Document đọc | Key đọc | Index chính |
|---|---|---:|---:|---:|---:|---|
| Q1 Top Action movies | `movies` | 10 | 0 ms | 10 | 29 | `genres.genreName_1_ratingStats.averageRating_-1_ratingStats.ratingCount_-1` |
| Q2 Person movies | `people` | 1 | 1 ms | 1 | 1 | `personName_1` |
| Q3 Actor ranking | `personCredits` | 10 | 9,517 ms | 560,837 | 1,122,881 | `roleName_1_personId_1_movieId_1` |
| Q3 Director ranking | `personCredits` | 10 | 806 ms | 48,999 | 97,998 | `roleName_1_personId_1_movieId_1` |
| Q4 Top genre by demographic | `ratings` | 36 | 235 ms | 99,810 | 0 | Collection scan |
| Q5 Country and age report | `ratings` | 1 pipeline result | 74 ms | 25,653 | 25,653 | `movieSnapshot.genres.genreName_1` |
| Q6 Company investment | `movies` | 5 | 267 ms | 45,433 | 0 | Collection scan |

Số liệu được ghi nhận ngày 06/08/2026. Trường `elapsedMillis` phía client lần lượt là 4, 7, 9.094, 756, 221, 72 và 258 ms.

## 3. Phân tích theo truy vấn

### 3.1. Q1

Compound index khớp điều kiện thể loại và thứ tự xếp hạng. MongoDB chỉ đọc gần bằng số document cần trả về.

### 3.2. Q2

Index `people.personName` tìm đúng hồ sơ trước khi lookup credit và phim. Việc bắt đầu từ `people` tránh quét toàn bộ `personCredits` cho một tên cụ thể.

### 3.3. Q3

Index theo `roleName`, `personId`, `movieId` hỗ trợ lọc vai trò và gom credit. Tuy nhiên truy vấn diễn viên vẫn phải xử lý hơn 560 nghìn credit trước khi xếp hạng, nên đây là truy vấn chậm nhất. Kết quả này là hệ quả có chủ đích của mô hình chuẩn hóa: không lưu thống kê tổng hợp trong `people` hoặc `personCredits`.

### 3.4. Q4

Q4 đọc toàn bộ `ratings`, bung `movieSnapshot.genres`, nhóm theo `userSnapshot.country`, `userSnapshot.ageGroup` và thể loại, áp dụng ngưỡng số lượt đánh giá, rồi chọn thể loại đứng đầu mỗi nhóm. Vì không có điều kiện lọc thể loại ở đầu pipeline, index genre snapshot không làm giảm tập đầu vào. Đổi lại, hệ thống không phải duy trì collection tổng hợp nhân khẩu học riêng.

### 3.5. Q5

Q5 có điều kiện thể loại cụ thể ngay đầu pipeline nên sử dụng index `movieSnapshot.genres.genreName_1`. Sau đó pipeline tạo dòng theo độ tuổi, subtotal theo quốc gia và grand total.

### 3.6. Q6

Q6 chạy trực tiếp trên `movies`. Một aggregation sơ bộ xác định năm thể loại có tổng doanh thu cao nhất; pipeline chính bung `companies` và dữ liệu thể loại nhúng để tính tổng tài chính công ty và tỷ lệ doanh thu/ngân sách theo thể loại.

Benchmark của pipeline chính đọc 45.433 phim trong khoảng 267 ms. Số này không bao gồm aggregation sơ bộ tìm năm thể loại, đúng với phạm vi hiện tại của script benchmark.

## 4. Đánh đổi kiến trúc

Q4 và Q6 xử lý nhiều document nguồn hơn tại thời điểm đọc so với cách dùng collection báo cáo dựng sẵn. Lợi ích là loại bỏ ba collection trung gian, tránh dữ liệu tổng hợp lỗi thời và đơn giản hóa quy tắc đồng bộ. `movies.ratingStats` vẫn được giữ vì trực tiếp tối ưu Q1 và có phạm vi đồng bộ nhỏ, rõ ràng.

Q3 diễn viên là điểm cần theo dõi nếu khối lượng credit tiếp tục tăng. Chỉ nên bổ sung cấu trúc tổng hợp khi có yêu cầu latency cụ thể; kiến trúc hiện tại ưu tiên tính đúng và nguồn dữ liệu duy nhất.

## 5. Chạy lại benchmark

```bash
make benchmark
```

Kết quả mới cần được đánh giá cùng quy mô collection, phiên bản MongoDB, cache và tải hệ thống trước khi so sánh.
