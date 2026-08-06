# Báo cáo hiệu năng truy vấn MongoDB

## 1. Môi trường đo

- MongoDB Server 8.3.7
- MongoDB Shell 2.9.2
- Database: `movie_analytics`
- Thời điểm đo: 2026-07-24
- Dữ liệu chính: 45.433 phim, 99.810 ratings, 221.746 người và 611.043 credits
- Công cụ: `explain("executionStats")` và thời gian thực thi đo tại client

Benchmark có thể chạy lại bằng:

```bash
mongosh "mongodb://localhost:27017/movie_analytics" --quiet \
  scripts/validation/benchmark_queries.js
```

Các số thời gian là kết quả trên máy cục bộ với cache đã được làm nóng, phù hợp để so sánh tương đối nhưng không đại diện cho mọi môi trường triển khai.

## 2. Kết quả trước khi tối ưu

| Truy vấn | Thời gian explain | Documents examined | Keys examined | Kế hoạch chính |
|---|---:|---:|---:|---|
| Q1 Top phim Action | 35 ms | 45.433 | 0 | `COLLSCAN` |
| Q2 Sự nghiệp cá nhân | 224 ms | 611.043 | 0 | `COLLSCAN` |
| Q3 Người tham gia nhiều phim | 460 ms | 221.746 | 0 | `COLLSCAN` |
| Q4 Thể loại theo nhân khẩu học | 2 ms | 696 | 0 | `COLLSCAN` |
| Q5 Báo cáo quốc gia và tuổi | 119 ms | 99.810 | 0 | `COLLSCAN` |
| Q6 Hiệu quả công ty | 395 ms | 98.367 | 20.905 | `COLLSCAN`, `_id_` lookup |

Nguyên nhân chính là index ban đầu ưu tiên ID tham chiếu, trong khi truy vấn trình diễn nhận tham số dạng tên. Q3 còn đặt `$project` trước `$sort`, làm mất khả năng dùng thứ tự của index.

## 3. Index bổ sung

```javascript
db.movies.createIndex({
  "genres.genreName": 1,
  "ratingStats.averageRating": -1,
  "ratingStats.ratingCount": -1
});

db.people.createIndex({personName: 1});

db.personCredits.createIndex({
  roleName: 1,
  personId: 1,
  movieId: 1
});

db.ratings.createIndex({"movieSnapshot.genres.genreName": 1});

db.demographicGenreStats.createIndex({
  country: 1,
  ageGroup: 1,
  averageRating: -1,
  ratingCount: -1
});

db.companyGenreStats.createIndex({genreName: 1, companyId: 1});
```

Q2 bắt đầu từ `people.personName`, sau đó lookup credit và phim. Q3 dùng index theo vai trò để group các cặp người-phim, rồi lookup `movies` và `people`; kết quả không phụ thuộc thống kê lưu sẵn.

## 4. Kết quả sau khi tối ưu

| Truy vấn | Kết quả | Thời gian explain | Documents examined | Keys examined | Index chính |
|---|---:|---:|---:|---:|---|
| Q1 Top phim Action | 10 | <1 ms | 10 | 29 | `genres.genreName_1_ratingStats.averageRating_-1_ratingStats.ratingCount_-1` |
| Q2 Sự nghiệp cá nhân | 1 | 1 ms | 1 | 1 | `personName_1` |
| Q3 Xếp hạng Actor | 10 | 8.873 ms | 560.837 | 1.122.881 | `roleName_1_personId_1_movieId_1`, `_id_` |
| Q3 Xếp hạng Director | 10 | 761 ms | 48.999 | 97.998 | `roleName_1_personId_1_movieId_1`, `_id_` |
| Q4 Thể loại theo nhân khẩu học | 36 | 3 ms | 696 | 696 | `country_1_ageGroup_1_averageRating_-1_ratingCount_-1` |
| Q5 Báo cáo quốc gia và tuổi | 1 báo cáo | 88 ms | 25.653 | 25.653 | `movieSnapshot.genres.genreName_1` |
| Q6 Hiệu quả công ty | 5 | 448 ms | 60.857 | 60.857 | `genreName_1_companyId_1`, `_id_` |

## 5. Đánh giá từng truy vấn

### Q1

Index bắt đầu bằng tên thể loại, tiếp theo là thứ tự điểm trung bình và số ratings. MongoDB chỉ đọc 29 khóa và fetch 10 phim để trả Top 10, thay vì quét toàn bộ 45.433 phim.

### Q2

Index `people.personName` xác định đúng hồ sơ Christopher Nolan trước khi lookup 14 phim qua `personCredits` và `movies`. Tên người, tên phim và doanh thu đều được đọc từ collection nguồn.

### Q3

Compound index `(roleName, personId, movieId)` hỗ trợ lọc vai trò và group theo người-phim. Vì không còn `careerStats`, truy vấn phải xử lý toàn bộ credit của vai trò tương ứng và lookup phim để tính điểm; đây là chi phí rõ ràng của mô hình chuẩn hóa đã chọn.

### Q4

Collection tổng hợp chỉ có 696 document nên quét toàn collection vẫn rẻ. Index loại bỏ bước sort tách biệt nhưng không làm giảm số document vì điều kiện `ratingCount >= 20` không nằm ở đầu index. Không cần thêm index khác cho quy mô hiện tại.

### Q5

Index genre snapshot giới hạn đầu vào còn 25.653 Action ratings thay vì toàn bộ 99.810 ratings. `$facet` vẫn phải đọc toàn bộ tập Action để tính chi tiết, subtotal và grand total, vì vậy đây là chi phí cần thiết của báo cáo chính xác.

### Q6

Index giảm số document examined từ 98.367 xuống 60.857. Truy vấn vẫn nặng nhất vì phải group 20.905 bản ghi thuộc năm thể loại, lookup thống kê công ty, tạo pivot và xếp hạng. Chênh lệch thời gian giữa hai lần đo không đáng tin cậy do cache và chi phí lookup; chỉ số documents examined thể hiện mức giảm công việc ổn định hơn.

Phép đo Q6 trong benchmark áp dụng cho pipeline công ty sau khi đã xác định năm thể loại doanh thu cao nhất. Bước xác định top thể loại chạy trực tiếp trên `movies` và chưa được cộng vào thời gian explain trong bảng.

## 6. Kết luận

Q1, Q2 và Q3 đạt cải thiện lớn nhất, không còn collection scan và chỉ đọc gần bằng số document cần trả về. Q5 giảm khoảng 74% số document phải đọc. Q4 đã đủ nhanh nhờ collection tổng hợp nhỏ. Q6 vẫn là truy vấn tốn tài nguyên nhất và là ứng viên phù hợp để minh họa đánh đổi giữa truy vấn động và materialized report trong phần bảo vệ đồ án.
