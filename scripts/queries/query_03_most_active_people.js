// Run: make query-3 LIMIT=10
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const limit = Number(process.env.LIMIT || 10);

function ranking(role, countField, ratingField) {
  return database.people
    .aggregate([
      { $match: { [countField]: { $gt: 0 } } },
      { $sort: { [countField]: -1, [ratingField]: -1 } },
      { $limit: limit },
      {
        $project: {
          _id: 0,
          personName: 1,
          role: { $literal: role },
          movieCount: `$${countField}`,
          averageMovieRating: `$${ratingField}`,
        },
      },
    ])
    .toArray();
}

console.log(`\nTop ${limit} most active actors`);
console.table(
  ranking(
    "Actor",
    "careerStats.actorMovieCount",
    "careerStats.actorAverageMovieRating",
  ),
);
console.log(`\nTop ${limit} most active directors`);
console.table(
  ranking(
    "Director",
    "careerStats.directorMovieCount",
    "careerStats.directorAverageMovieRating",
  ),
);
