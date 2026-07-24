#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def inspect(dataset_dir: Path) -> dict:
    metadata_ids = set()
    metadata_rows = 0
    metadata_bad_ids = 0
    metadata_duplicate_ids = 0

    with (dataset_dir / "movies_metadata.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            metadata_rows += 1
            try:
                tmdb_id = int(row["id"])
            except (TypeError, ValueError):
                metadata_bad_ids += 1
                continue
            if tmdb_id in metadata_ids:
                metadata_duplicate_ids += 1
            metadata_ids.add(tmdb_id)

    links = {}
    links_rows = 0
    links_missing_tmdb = 0
    duplicate_movie_lens_ids = 0
    with (dataset_dir / "links_small.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            links_rows += 1
            movie_lens_id = int(row["movieId"])
            if movie_lens_id in links:
                duplicate_movie_lens_ids += 1
            raw_tmdb_id = row["tmdbId"].strip()
            tmdb_id = int(float(raw_tmdb_id)) if raw_tmdb_id else None
            if tmdb_id is None:
                links_missing_tmdb += 1
            links[movie_lens_id] = tmdb_id

    users = set()
    rated_movies = set()
    rating_distribution = Counter()
    pairs = set()
    duplicate_pairs = 0
    rating_rows = 0
    joined_ratings = 0
    missing_link_ratings = 0
    missing_metadata_ratings = 0

    with (dataset_dir / "ratings_small.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            rating_rows += 1
            user_id = int(row["userId"])
            movie_lens_id = int(row["movieId"])
            rating = float(row["rating"])
            users.add(user_id)
            rated_movies.add(movie_lens_id)
            rating_distribution[rating] += 1
            pair = (user_id, movie_lens_id)
            if pair in pairs:
                duplicate_pairs += 1
            pairs.add(pair)

            if movie_lens_id not in links or links[movie_lens_id] is None:
                missing_link_ratings += 1
            elif links[movie_lens_id] not in metadata_ids:
                missing_metadata_ratings += 1
            else:
                joined_ratings += 1

    return {
        "metadata": {
            "rows": metadata_rows,
            "uniqueValidTmdbIds": len(metadata_ids),
            "badIdRows": metadata_bad_ids,
            "duplicateIdRows": metadata_duplicate_ids,
        },
        "links": {
            "rows": links_rows,
            "uniqueMovieLensIds": len(links),
            "missingTmdbIds": links_missing_tmdb,
            "duplicateMovieLensIds": duplicate_movie_lens_ids,
        },
        "ratingsSmall": {
            "rows": rating_rows,
            "users": len(users),
            "distinctMovies": len(rated_movies),
            "joinedRows": joined_ratings,
            "joinedPercent": round(joined_ratings * 100 / rating_rows, 4),
            "rejectedRows": rating_rows - joined_ratings,
            "missingLinkRows": missing_link_ratings,
            "missingMetadataRows": missing_metadata_ratings,
            "duplicateUserMoviePairs": duplicate_pairs,
            "distribution": dict(sorted(rating_distribution.items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and validate the movie dataset")
    parser.add_argument("--dataset-dir", type=Path, default=Path("dataset"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect(args.dataset_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
