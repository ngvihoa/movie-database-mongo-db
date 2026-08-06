# Kiến trúc collection MongoDB

## 1. Mục tiêu thiết kế

Mô hình MongoDB được tổ chức theo sáu truy vấn phân tích của hệ thống. Thiết kế ưu tiên:

- giữ thực thể dùng chung bằng reference;
- embed dữ liệu có kích thước hữu hạn và thường được đọc cùng document cha;
- giữ snapshot cần thiết trong `ratings` để phân tích theo thời điểm đánh giá;
- tổng hợp trực tiếp từ collection nghiệp vụ thay vì duy trì collection báo cáo riêng;
- chỉ lưu `movies.ratingStats` như thống kê nhúng có thể xây dựng lại.

Kiến trúc có 8 collection nghiệp vụ. `etlRejects` là collection kỹ thuật phục vụ kiểm soát dữ liệu và không thuộc mô hình nghiệp vụ.

## 2. Danh sách collection

1. `movieCollections`
2. `genres`
3. `companies`
4. `movies`
5. `users`
6. `ratings`
7. `people`
8. `personCredits`

Ba collection cũ `companyMovies`, `demographicGenreStats` và `companyGenreStats` không còn thuộc kiến trúc. `scripts/setup/setup_database.py` xóa chúng khi migration. Trường cũ `companies.companyStats` cũng được loại bỏ.

## 3. Cấu trúc document

### 3.1. `movieCollections`

```javascript
{
  _id: ObjectId,
  sourceIds: { tmdbId: Number },
  collectionName: String,
  posterPath: String,
  backdropPath: String,
  createdAt: Date,
  updatedAt: Date
}
```

### 3.2. `genres`

```javascript
{
  _id: ObjectId,
  sourceIds: { tmdbId: Number },
  genreName: String,
  createdAt: Date,
  updatedAt: Date
}
```

### 3.3. `companies`

```javascript
{
  _id: ObjectId,
  sourceIds: { tmdbId: Number },
  companyName: String,
  createdAt: Date,
  updatedAt: Date
}
```

`companies` chỉ lưu hồ sơ công ty. Thống kê tài chính được Q6 tính trực tiếp từ `movies`.

### 3.4. `movies`

```javascript
{
  _id: ObjectId,
  sourceIds: { tmdbId: Number, movieLensId: Number },
  title: String,
  releaseDate: Date,
  runtime: Number,
  budget: NumberLong,
  revenue: NumberLong,
  collection: {
    collectionId: ObjectId,
    collectionName: String
  },
  genres: [{ genreId: ObjectId, genreName: String }],
  companies: [{ companyId: ObjectId, companyName: String }],
  productionCountries: [{ isoCode: String, countryName: String }],
  ratingStats: {
    ratingCount: Number,
    averageRating: Number
  },
  createdAt: Date,
  updatedAt: Date
}
```

`genres`, `companies` và `collection` được embed ở dạng tham chiếu kèm tên để các truy vấn phim không cần `$lookup`. `ratingStats` được làm mới từ `ratings` bằng `make rebuild`.

### 3.5. `users`

```javascript
{
  _id: ObjectId,
  sourceIds: { movieLensUserId: Number },
  profile: {
    birthYear: Number,
    ageGroup: String,
    country: String
  },
  createdAt: Date,
  updatedAt: Date
}
```

### 3.6. `ratings`

```javascript
{
  _id: ObjectId,
  userId: ObjectId,
  movieId: ObjectId,
  rating: Number,
  ratedAt: Date,
  userSnapshot: {
    ageGroup: String,
    country: String
  },
  movieSnapshot: {
    genres: [{ genreId: ObjectId, genreName: String }]
  },
  createdAt: Date,
  updatedAt: Date
}
```

Snapshot giúp Q4 và Q5 phân tích theo thuộc tính tại thời điểm ghi nhận mà không cần join `users` và `movies`.

### 3.7. `people`

```javascript
{
  _id: ObjectId,
  sourceIds: { tmdbId: Number },
  personName: String,
  gender: Number,
  profilePath: String,
  createdAt: Date,
  updatedAt: Date
}
```

### 3.8. `personCredits`

```javascript
{
  _id: ObjectId,
  personId: ObjectId,
  movieId: ObjectId,
  creditKind: String,
  roleName: String,
  characterName: String,
  billingOrder: Number,
  createdAt: Date,
  updatedAt: Date
}
```

`personCredits` chỉ lưu reference và thuộc tính vai trò. Tên người, tên phim và thống kê phim không được lặp lại trong collection này.

## 4. Quan hệ logic

```text
movieCollections -> movies.collection
genres           -> movies.genres
genres           -> ratings.movieSnapshot.genres
companies        -> movies.companies
users            -> ratings.userId
movies           -> ratings.movieId
movies           -> personCredits.movieId
people           -> personCredits.personId
```

## 5. Mapping sáu truy vấn

| Truy vấn | Collection bắt đầu | Cách xử lý |
|---|---|---|
| Q1 Top phim Action | `movies` | Lọc `genres.genreName` và đọc `ratingStats` |
| Q2 Phim của một người | `people` | `$lookup` `personCredits`, sau đó `$lookup` `movies` |
| Q3 Người hoạt động nhiều nhất | `personCredits` | Nhóm theo người/phim rồi `$lookup` `people` và `movies` |
| Q4 Thể loại theo nhân khẩu học | `ratings` | Bung `movieSnapshot.genres`, nhóm theo snapshot quốc gia, độ tuổi và thể loại |
| Q5 Báo cáo quốc gia, độ tuổi | `ratings` | Lọc thể loại snapshot rồi tạo chi tiết, subtotal và grand total |
| Q6 Hiệu quả đầu tư công ty | `movies` | Xác định 5 thể loại doanh thu cao nhất, sau đó bung `companies` và `genres` để tổng hợp trực tiếp |

Q4 chọn thể loại có điểm trung bình cao nhất trong từng nhóm nhân khẩu học sau khi áp dụng ngưỡng số lượt đánh giá. Q6 tính tỷ lệ doanh thu/ngân sách tổng thể và theo thể loại ngay tại thời điểm truy vấn.

## 6. Index chính

```javascript
db.movies.createIndex({
  "genres.genreName": 1,
  "ratingStats.averageRating": -1,
  "ratingStats.ratingCount": -1
});
db.movies.createIndex({"companies.companyId": 1});
db.people.createIndex({personName: 1});
db.personCredits.createIndex({roleName: 1, personId: 1, movieId: 1});
db.ratings.createIndex({"movieSnapshot.genres.genreName": 1});
```

Setup còn tạo các unique index cho mã nguồn và các index reference cần thiết để bảo đảm toàn vẹn và hỗ trợ lookup.

## 7. Đồng bộ dữ liệu

- Khi rating thay đổi, chạy `make rebuild` để làm mới `movies.ratingStats`.
- `ratings.userSnapshot` và `ratings.movieSnapshot.genres` được tạo khi import và được giữ như dữ liệu lịch sử của đánh giá.
- Khi chính sách yêu cầu snapshot phản ánh dữ liệu phim hiện hành, thay đổi thể loại phim phải được đồng bộ riêng vào rating liên quan.
- Q2 và Q3 luôn đọc hồ sơ người và phim hiện hành qua `$lookup`; không có thống kê hoặc tên bị sao chép trong miền người-phim.
- Q4 và Q6 đọc trực tiếp collection nghiệp vụ nên không có collection tổng hợp phải đồng bộ.

`scripts/aggregate/rebuild_derived.js` chỉ làm mới `movies.ratingStats` và dọn các trường legacy. Script không tạo collection báo cáo dẫn xuất.

## 8. Kết luận

Mô hình 8 collection giữ chuẩn hóa cho danh mục và miền người-phim, đồng thời embed các chiều nhỏ phục vụ truy vấn phim. Rating snapshot hỗ trợ phân tích nhân khẩu học, còn Q4 và Q6 chấp nhận chi phí tổng hợp tại thời điểm đọc để loại bỏ chi phí đồng bộ của ba collection trung gian.
