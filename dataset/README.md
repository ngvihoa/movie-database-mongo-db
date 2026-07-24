# Nguồn dữ liệu

Dữ liệu trong thư mục này được lấy từ **The Movies Dataset** trên Kaggle:

- Tác giả: Rounak Banik
- Năm phát hành: 2017
- Phiên bản: 7
- Cập nhật lần cuối: 10/11/2017
- Nguồn: <https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset>
- Giấy phép trên Kaggle: [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/)

Bộ dữ liệu tổng hợp metadata của hơn 45.000 phim từ TMDB cùng dữ liệu liên kết và đánh giá phim từ GroupLens MovieLens. Sản phẩm này sử dụng TMDB API nhưng không được TMDB chứng thực hoặc chứng nhận.

## Dữ liệu sử dụng trong dự án

Dự án sử dụng các file sau:

- `movies_metadata.csv`: metadata phim từ TMDB.
- `credits.csv`: thông tin diễn viên và đoàn làm phim.
- `links_small.csv`: ánh xạ MovieLens ID sang TMDB ID và IMDb ID.
- `ratings_small.csv`: 100.004 lượt đánh giá thuộc tập MovieLens nhỏ.

File `ratings.csv` thuộc bộ dữ liệu tải về nhưng không được sử dụng trong pipeline ETL của dự án.

## Trích dẫn

### APA 7

Banik, R. (2017). *The Movies Dataset* (Version 7) [Data set]. Kaggle. https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset

Ngày truy cập: 25/07/2026.

### BibTeX

```bibtex
@dataset{banik2017movies,
  author    = {Rounak Banik},
  title     = {The Movies Dataset},
  year      = {2017},
  version   = {7},
  publisher = {Kaggle},
  url       = {https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset},
  note      = {Accessed: 2026-07-25}
}
```

## Nguồn dữ liệu thành phần

- TMDB API: <https://developer.themoviedb.org/docs/getting-started>
- GroupLens MovieLens: <https://grouplens.org/datasets/movielens/>

Thông tin tác giả, phiên bản, giấy phép và nguồn dữ liệu thành phần ở trên được đối chiếu từ trang Kaggle và metadata API của bộ dữ liệu.
