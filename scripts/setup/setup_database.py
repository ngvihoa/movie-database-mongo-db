#!/usr/bin/env python3
import argparse
import os

from pymongo import ASCENDING, DESCENDING, MongoClient


COLLECTIONS = [
    "movieCollections",
    "genres",
    "companies",
    "movies",
    "users",
    "ratings",
    "people",
    "personCredits",
    "companyMovies",
    "demographicGenreStats",
    "companyGenreStats",
    "etlRejects",
]

VALIDATORS = {
    "movies": {"$jsonSchema": {
        "bsonType": "object",
        "required": ["sourceIds", "title", "genres", "companies", "ratingStats"],
        "properties": {
            "sourceIds": {"bsonType": "object", "required": ["tmdbId"], "properties": {
                "tmdbId": {"bsonType": ["int", "long"]},
                "movieLensId": {"bsonType": ["int", "long"]},
                "imdbId": {"bsonType": "string"},
            }},
            "title": {"bsonType": "string"},
            "budget": {"bsonType": ["int", "long"]},
            "revenue": {"bsonType": ["int", "long"]},
            "genres": {"bsonType": "array"},
            "companies": {"bsonType": "array"},
        },
    }},
    "users": {"$jsonSchema": {
        "bsonType": "object",
        "required": ["sourceIds", "age", "ageGroup", "country", "isSynthetic"],
        "properties": {
            "age": {"bsonType": "int", "minimum": 0},
            "ageGroup": {"enum": ["Under 18", "18-24", "25-34", "35-44", "45-54", "55+"]},
            "country": {"bsonType": "string"},
            "isSynthetic": {"bsonType": "bool"},
        },
    }},
    "ratings": {"$jsonSchema": {
        "bsonType": "object",
        "required": ["userId", "movieId", "rating", "ratedAt", "userSnapshot", "movieSnapshot"],
        "properties": {
            "userId": {"bsonType": "objectId"},
            "movieId": {"bsonType": "objectId"},
            "rating": {"bsonType": "double", "minimum": 0.5, "maximum": 5.0},
            "ratedAt": {"bsonType": "date"},
        },
    }},
}


def ensure_collections(database) -> None:
    existing = set(database.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            database.create_collection(name)
    for name, validator in VALIDATORS.items():
        database.command({
            "collMod": name,
            "validator": validator,
            "validationLevel": "strict",
            "validationAction": "error",
        })


def ensure_indexes(database) -> None:
    database.movieCollections.create_index("sourceIds.tmdbId", unique=True)
    database.movieCollections.create_index("collectionName", unique=True)
    database.genres.create_index("sourceIds.tmdbId", unique=True)
    database.genres.create_index("genreName", unique=True)
    database.companies.create_index("sourceIds.tmdbId", unique=True)
    database.companies.create_index("companyName")
    database.movies.create_index("sourceIds.tmdbId", unique=True)
    database.movies.create_index("sourceIds.movieLensId", unique=True, sparse=True)
    database.movies.create_index("title")
    database.movies.create_index([
        ("genres.genreId", ASCENDING),
        ("ratingStats.ratingCount", DESCENDING),
        ("ratingStats.averageRating", DESCENDING),
    ])
    database.movies.create_index([
        ("genres.genreName", ASCENDING),
        ("ratingStats.averageRating", DESCENDING),
        ("ratingStats.ratingCount", DESCENDING),
    ])
    database.movies.create_index("companies.companyId")
    database.users.create_index("sourceIds.movieLensUserId", unique=True)
    database.users.create_index([("country", ASCENDING), ("ageGroup", ASCENDING)])
    database.ratings.create_index([("userId", ASCENDING), ("movieId", ASCENDING)], unique=True)
    database.ratings.create_index([("movieId", ASCENDING), ("ratedAt", DESCENDING)])
    database.ratings.create_index([
        ("userSnapshot.country", ASCENDING),
        ("userSnapshot.ageGroup", ASCENDING),
        ("movieSnapshot.genres.genreId", ASCENDING),
    ])
    database.ratings.create_index("movieSnapshot.genres.genreName")
    database.people.create_index("sourceIds.tmdbId", unique=True)
    database.people.create_index("personName")
    database.people.create_index([
        ("careerStats.movieCount", DESCENDING),
        ("careerStats.averageMovieRating", DESCENDING),
    ])
    database.people.create_index([
        ("careerStats.actorMovieCount", DESCENDING),
        ("careerStats.actorAverageMovieRating", DESCENDING),
    ])
    database.people.create_index([
        ("careerStats.directorMovieCount", DESCENDING),
        ("careerStats.directorAverageMovieRating", DESCENDING),
    ])
    database.personCredits.create_index([
        ("personId", ASCENDING), ("roleName", ASCENDING), ("movieId", ASCENDING)
    ])
    database.personCredits.create_index([("personName", ASCENDING), ("roleName", ASCENDING)])
    database.personCredits.create_index("sourceIds.creditId", unique=True)
    database.companyMovies.create_index([("companyId", ASCENDING), ("movieId", ASCENDING)], unique=True)
    database.demographicGenreStats.create_index([
        ("genreId", ASCENDING), ("country", ASCENDING), ("ageGroup", ASCENDING)
    ], unique=True)
    database.demographicGenreStats.create_index([
        ("country", ASCENDING), ("ageGroup", ASCENDING),
        ("averageRating", DESCENDING), ("ratingCount", DESCENDING),
    ])
    database.companyGenreStats.create_index([
        ("companyId", ASCENDING), ("genreId", ASCENDING)
    ], unique=True)
    database.companyGenreStats.create_index([("genreName", ASCENDING), ("companyId", ASCENDING)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Create MongoDB collections and indexes")
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--database", default=os.getenv("MONGODB_DATABASE", "movie_analytics"))
    args = parser.parse_args()
    client = MongoClient(args.uri)
    database = client[args.database]
    ensure_collections(database)
    ensure_indexes(database)
    print(f"MongoDB database ready: {args.database}")


if __name__ == "__main__":
    main()
