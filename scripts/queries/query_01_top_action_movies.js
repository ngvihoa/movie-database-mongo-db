// Run: make query-1
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const rows = database.movies
  .find(
    { "genres.genreName": "Action", "ratingStats.ratingCount": { $gte: 50 } },
    {
      _id: 0,
      title: 1,
      averageRating: "$ratingStats.averageRating",
      ratingCount: "$ratingStats.ratingCount",
    },
  )
  .sort({ "ratingStats.averageRating": -1, "ratingStats.ratingCount": -1 })
  .limit(10)
  .toArray();

console.log("\nTop 10 Action movies (minimum 50 ratings)");
console.table(rows);
