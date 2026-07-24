// Run: mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_03_most_active_people.js
const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
const limit = Number(process.env.LIMIT || 10);

function ranking(role, countField, ratingField) {
  return database.people.aggregate([
    {$match: {[countField]: {$gt: 0}}},
    {$sort: {[countField]: -1, [ratingField]: -1}},
    {$limit: limit},
    {$project: {
      _id: 0,
      personName: 1,
      role: {$literal: role},
      movieCount: `$${countField}`,
      averageMovieRating: `$${ratingField}`,
    }},
  ]).toArray();
}

printjson({
  actors: ranking("Actor", "careerStats.actorMovieCount", "careerStats.actorAverageMovieRating"),
  directors: ranking("Director", "careerStats.directorMovieCount", "careerStats.directorAverageMovieRating"),
});
