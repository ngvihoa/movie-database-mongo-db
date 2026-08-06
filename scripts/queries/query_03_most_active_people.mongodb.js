// Run: make query-3 LIMIT=10
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const limit = Number(process.env.LIMIT || 10);

function ranking(role) {
  return database.personCredits
    .aggregate([
      { $match: { roleName: role } },
      { $group: { _id: { personId: "$personId", movieId: "$movieId" } } },
      {
        $lookup: {
          from: "movies",
          localField: "_id.movieId",
          foreignField: "_id",
          as: "movie",
        },
      },
      { $set: { movie: { $first: "$movie" } } },
      {
        $group: {
          _id: "$_id.personId",
          movieCount: { $sum: 1 },
          averageMovieRating: {
            $avg: {
              $cond: [
                { $gt: [{ $ifNull: ["$movie.ratingStats.ratingCount", 0] }, 0] },
                "$movie.ratingStats.averageRating",
                null,
              ],
            },
          },
        },
      },
      {
        $lookup: {
          from: "people",
          localField: "_id",
          foreignField: "_id",
          as: "person",
        },
      },
      { $set: { person: { $first: "$person" } } },
      { $sort: { movieCount: -1, averageMovieRating: -1 } },
      { $limit: limit },
      {
        $project: {
          _id: 0,
          personName: "$person.personName",
          role: { $literal: role },
          movieCount: 1,
          averageMovieRating: { $round: ["$averageMovieRating", 4] },
        },
      },
    ])
    .toArray();
}

console.log(`\nTop ${limit} most active actors`);
console.table(ranking("Actor"));
console.log(`\nTop ${limit} most active directors`);
console.table(ranking("Director"));
