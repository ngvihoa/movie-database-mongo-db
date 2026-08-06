#!/usr/bin/env python3
import argparse
import ast
import csv
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient, ReplaceOne, UpdateOne


COUNTRIES = ["Vietnam", "United States", "Japan", "South Korea", "France", "Germany"]
AGE_GROUPS = [
    (17, "Under 18"), (24, "18-24"), (34, "25-34"),
    (44, "35-44"), (54, "45-54"), (75, "55+"),
]


def parse_literal(value, default):
    if not value:
        return default
    try:
        parsed = ast.literal_eval(value)
        return parsed if parsed is not None else default
    except (ValueError, SyntaxError):
        return default


def parse_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def flush(collection, operations):
    if operations:
        collection.bulk_write(operations, ordered=False)
        operations.clear()


class Importer:
    def __init__(self, database, dataset_dir: Path, batch_size: int, user_seed: int):
        self.db = database
        self.dataset_dir = dataset_dir
        self.batch_size = batch_size
        self.user_seed = user_seed
        self.now = datetime.now(timezone.utc)
        self.stats = {}

    def import_movies(self):
        links_by_tmdb = {}
        with (self.dataset_dir / "links_small.csv").open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row["tmdbId"].strip():
                    links_by_tmdb[parse_int(row["tmdbId"])] = {
                        "movieLensId": parse_int(row["movieId"]),
                        "imdbId": f"tt{row['imdbId'].zfill(7)}",
                    }

        genres = {}
        companies = {}
        collections = {}
        movie_rows = []
        rejected = 0
        seen_tmdb_ids = set()

        with (self.dataset_dir / "movies_metadata.csv").open(encoding="utf-8", newline="") as file:
            for line_number, row in enumerate(csv.DictReader(file), 2):
                try:
                    tmdb_id = int(row["id"])
                except (TypeError, ValueError):
                    self.reject("movies_metadata", line_number, "INVALID_TMDB_ID", row.get("id"))
                    rejected += 1
                    continue
                if tmdb_id in seen_tmdb_ids:
                    self.reject("movies_metadata", line_number, "DUPLICATE_TMDB_ID", tmdb_id)
                    rejected += 1
                    continue
                seen_tmdb_ids.add(tmdb_id)

                row_genres = parse_literal(row["genres"], [])
                row_companies = parse_literal(row["production_companies"], [])
                row_collection = parse_literal(row["belongs_to_collection"], {})
                for genre in row_genres:
                    if genre.get("id") is not None:
                        genres[int(genre["id"])] = genre.get("name")
                for company in row_companies:
                    if company.get("id") is not None:
                        companies[int(company["id"])] = company.get("name")
                if row_collection and row_collection.get("id") is not None:
                    collections[int(row_collection["id"])] = row_collection.get("name")
                movie_rows.append((tmdb_id, row, row_genres, row_companies, row_collection))

        self.upsert_catalog("genres", "genreName", genres)
        self.upsert_catalog("companies", "companyName", companies)
        self.upsert_catalog("movieCollections", "collectionName", collections)
        genre_ids = self.source_id_map("genres")
        company_ids = self.source_id_map("companies")
        collection_ids = self.source_id_map("movieCollections")

        operations = []
        for tmdb_id, row, row_genres, row_companies, row_collection in movie_rows:
            source_ids = {"tmdbId": tmdb_id}
            source_ids.update(links_by_tmdb.get(tmdb_id, {}))
            countries = parse_literal(row["production_countries"], [])
            document = {
                "sourceIds": source_ids,
                "title": row["title"] or row["original_title"] or f"Untitled ({tmdb_id})",
                "originalTitle": row["original_title"] or row["title"] or None,
                "overview": row["overview"] or None,
                "releaseDate": parse_date(row["release_date"]),
                "runtime": parse_int(row["runtime"], None),
                "status": row["status"] or None,
                "budget": parse_int(row["budget"]),
                "revenue": parse_int(row["revenue"]),
                "productionCountries": [
                    {"countryCode": item.get("iso_3166_1"), "countryName": item.get("name")}
                    for item in countries
                ],
                "collection": (
                    {"collectionId": collection_ids[int(row_collection["id"])],
                     "collectionName": row_collection.get("name")}
                    if row_collection and int(row_collection["id"]) in collection_ids else None
                ),
                "genres": [
                    {"genreId": genre_ids[int(item["id"])], "genreName": item.get("name")}
                    for item in row_genres if int(item["id"]) in genre_ids
                ],
                "companies": [
                    {"companyId": company_ids[int(item["id"])], "companyName": item.get("name")}
                    for item in row_companies if int(item["id"]) in company_ids
                ],
                "sourceRatingStats": {
                    "averageRating": parse_float(row["vote_average"]),
                    "ratingCount": parse_int(row["vote_count"]),
                },
                "ratingStats": {"averageRating": 0.0, "ratingCount": 0},
                "updatedAt": self.now,
            }
            operations.append(UpdateOne(
                {"sourceIds.tmdbId": tmdb_id},
                {"$set": document, "$setOnInsert": {"createdAt": self.now}},
                upsert=True,
            ))
            if len(operations) >= self.batch_size:
                flush(self.db.movies, operations)
        flush(self.db.movies, operations)
        self.stats["movies"] = {"imported": len(movie_rows), "rejected": rejected}

    def upsert_catalog(self, collection_name, name_field, values):
        collection = self.db[collection_name]
        operations = [UpdateOne(
            {"sourceIds.tmdbId": source_id},
            {"$set": {name_field: name, "updatedAt": self.now},
             "$setOnInsert": {"createdAt": self.now}},
            upsert=True,
        ) for source_id, name in values.items()]
        for offset in range(0, len(operations), self.batch_size):
            collection.bulk_write(operations[offset:offset + self.batch_size], ordered=False)

    def source_id_map(self, collection_name):
        return {
            document["sourceIds"]["tmdbId"]: document["_id"]
            for document in self.db[collection_name].find({}, {"sourceIds.tmdbId": 1})
        }

    def import_credits(self):
        movie_ids = self.source_id_map("movies")
        people = {}
        credit_rows = []
        rejected = 0
        with (self.dataset_dir / "credits.csv").open(encoding="utf-8", newline="") as file:
            for line_number, row in enumerate(csv.DictReader(file), 2):
                tmdb_movie_id = parse_int(row["id"], None)
                if tmdb_movie_id not in movie_ids:
                    rejected += 1
                    continue
                for item in parse_literal(row["cast"], []):
                    if item.get("id") is None:
                        continue
                    person_id = int(item["id"])
                    people[person_id] = item.get("name")
                    credit_rows.append((tmdb_movie_id, person_id, "CAST", "Actor", "Acting", item))
                for item in parse_literal(row["crew"], []):
                    if item.get("id") is None or item.get("job") != "Director":
                        continue
                    person_id = int(item["id"])
                    people[person_id] = item.get("name")
                    credit_rows.append((tmdb_movie_id, person_id, "CREW", "Director", item.get("department"), item))

        self.upsert_catalog("people", "personName", people)
        person_ids = self.source_id_map("people")
        operations = []
        for tmdb_movie_id, tmdb_person_id, credit_type, role, department, item in credit_rows:
            credit_id = item.get("credit_id") or f"{credit_type}:{tmdb_person_id}:{tmdb_movie_id}:{item.get('character', '')}"
            document = {
                "sourceIds": {"creditId": credit_id},
                "personId": person_ids[tmdb_person_id],
                "movieId": movie_ids[tmdb_movie_id],
                "creditType": credit_type,
                "roleName": role,
                "department": department,
                "characterName": item.get("character") if credit_type == "CAST" else None,
                "creditOrder": item.get("order") if credit_type == "CAST" else None,
                "updatedAt": self.now,
            }
            operations.append(UpdateOne(
                {"sourceIds.creditId": credit_id},
                {
                    "$set": document,
                    "$unset": {"personName": "", "movieTitle": "", "movieStats": ""},
                    "$setOnInsert": {"createdAt": self.now},
                },
                upsert=True,
            ))
            if len(operations) >= self.batch_size:
                flush(self.db.personCredits, operations)
        flush(self.db.personCredits, operations)
        self.stats["personCredits"] = {"imported": len(credit_rows), "rejectedMovieRows": rejected}

    def import_users(self):
        user_source_ids = set()
        with (self.dataset_dir / "ratings_small.csv").open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                user_source_ids.add(int(row["userId"]))
        operations = []
        for source_id in sorted(user_source_ids):
            randomizer = random.Random(self.user_seed + source_id)
            age = randomizer.randint(14, 75)
            age_group = next(label for maximum, label in AGE_GROUPS if age <= maximum)
            document = {
                "sourceIds": {"movieLensUserId": source_id},
                "name": f"User {source_id}",
                "email": f"user{source_id}@example.test",
                "age": age,
                "ageGroup": age_group,
                "country": randomizer.choice(COUNTRIES),
                "updatedAt": self.now,
            }
            operations.append(UpdateOne(
                {"sourceIds.movieLensUserId": source_id},
                {"$set": document, "$setOnInsert": {"createdAt": self.now}}, upsert=True
            ))
        flush(self.db.users, operations)
        self.stats["users"] = {"imported": len(user_source_ids)}

    def import_ratings(self):
        links = {}
        with (self.dataset_dir / "links_small.csv").open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                links[int(row["movieId"])] = parse_int(row["tmdbId"], None) if row["tmdbId"].strip() else None
        movies = {
            document["sourceIds"]["tmdbId"]: document
            for document in self.db.movies.find({}, {"sourceIds.tmdbId": 1, "genres": 1})
        }
        users = {
            document["sourceIds"]["movieLensUserId"]: document
            for document in self.db.users.find({}, {"sourceIds.movieLensUserId": 1, "country": 1, "ageGroup": 1})
        }
        operations = []
        imported = rejected = 0
        with (self.dataset_dir / "ratings_small.csv").open(encoding="utf-8", newline="") as file:
            for line_number, row in enumerate(csv.DictReader(file), 2):
                movie_lens_id = int(row["movieId"])
                tmdb_id = links.get(movie_lens_id)
                if tmdb_id not in movies:
                    self.reject("ratings_small", line_number, "MOVIE_NOT_MAPPED", movie_lens_id)
                    rejected += 1
                    continue
                source_user_id = int(row["userId"])
                movie = movies[tmdb_id]
                user = users[source_user_id]
                document = {
                    "userId": user["_id"],
                    "movieId": movie["_id"],
                    "rating": float(row["rating"]),
                    "ratedAt": datetime.fromtimestamp(int(row["timestamp"]), timezone.utc),
                    "userSnapshot": {"country": user["country"], "ageGroup": user["ageGroup"]},
                    "movieSnapshot": {"genres": movie.get("genres", [])},
                    "sourceIds": {"movieLensUserId": source_user_id, "movieLensMovieId": movie_lens_id},
                    "updatedAt": self.now,
                }
                operations.append(UpdateOne(
                    {"userId": user["_id"], "movieId": movie["_id"]},
                    {"$set": document, "$setOnInsert": {"createdAt": self.now}}, upsert=True
                ))
                imported += 1
                if len(operations) >= self.batch_size:
                    flush(self.db.ratings, operations)
        flush(self.db.ratings, operations)
        self.stats["ratings"] = {"imported": imported, "rejected": rejected}

    def reject(self, source, line_number, reason, value):
        self.db.etlRejects.update_one(
            {"source": source, "lineNumber": line_number, "reason": reason},
            {"$set": {"value": value, "updatedAt": self.now}},
            upsert=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Import The Movies Dataset into MongoDB")
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--database", default=os.getenv("MONGODB_DATABASE", "movie_analytics"))
    parser.add_argument("--dataset-dir", type=Path, default=Path(os.getenv("DATASET_DIR", "dataset")))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("ETL_BATCH_SIZE", "5000")))
    parser.add_argument("--user-seed", type=int, default=int(os.getenv("USER_SEED", "2026")))
    args = parser.parse_args()
    client = MongoClient(args.uri)
    importer = Importer(client[args.database], args.dataset_dir, args.batch_size, args.user_seed)
    importer.import_movies()
    importer.import_credits()
    importer.import_users()
    importer.import_ratings()
    print(importer.stats)


if __name__ == "__main__":
    main()
