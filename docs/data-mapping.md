# Ánh xạ dữ liệu nguồn

## Chuỗi định danh phim

Không nối trực tiếp `ratings_small.movieId` với `movies_metadata.id`.

```text
ratings_small.movieId (MovieLens)
  -> links_small.movieId
  -> links_small.tmdbId
  -> movies_metadata.id (TMDB)
```

Các ID nguồn được giữ trong `movies.sourceIds` để truy vết và chống nhập trùng.

## Movies

| CSV | MongoDB |
|---|---|
| `id` | `sourceIds.tmdbId` |
| `links_small.movieId` | `sourceIds.movieLensId` |
| `imdb_id` | `sourceIds.imdbId` |
| `title` | `title` |
| `release_date` | `releaseDate` |
| `budget` | `budget` |
| `revenue` | `revenue` |
| `genres` | `genres[]` |
| `production_companies` | `companies[]` |
| `production_countries` | `productionCountries[]` |
| `vote_average`, `vote_count` | `sourceRatingStats` |

`ratingStats` không lấy từ metadata mà được tính lại từ `ratings`.

## Credits

`credits.cast` tạo `people` và các credit có `roleName: "Actor"`. Chỉ crew có `job: "Director"` được nhập vì đây là phạm vi khai thác hiện tại.

## Users

MovieLens chỉ cung cấp `userId`. Tuổi và quốc gia được sinh bằng seed cố định, có `isSynthetic: true`, và không được trình bày như dữ liệu nhân khẩu học thực tế.

## Ratings

Chỉ rating ánh xạ đầy đủ sang một phim TMDB được nhập. Với dataset hiện tại:

- Đầu vào: 100.004
- Hợp lệ: 99.810
- Bị loại: 194
- Thiếu TMDB ID trong links: 71
- Có TMDB ID nhưng thiếu metadata: 123

Các dòng bị loại được ghi vào `etlRejects`.
