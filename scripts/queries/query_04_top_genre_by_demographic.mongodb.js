// Run: make query-4 MIN_RATINGS=20
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const minimumRatings = Number(process.env.MIN_RATINGS || 20);
const rows = database.demographicGenreStats
  .aggregate([
    { $match: { ratingCount: { $gte: minimumRatings } } },
    { $sort: { country: 1, ageGroup: 1, averageRating: -1, ratingCount: -1 } },
    {
      $group: {
        _id: { country: "$country", ageGroup: "$ageGroup" },
        topGenre: { $first: "$genreName" },
        averageRating: { $first: "$averageRating" },
        ratingCount: { $first: "$ratingCount" },
      },
    },
    {
      $project: {
        _id: 0,
        country: "$_id.country",
        ageGroup: "$_id.ageGroup",
        topGenre: 1,
        averageRating: 1,
        ratingCount: 1,
      },
    },
    { $sort: { country: 1, ageGroup: 1 } },
  ])
  .toArray();

console.log(`\nTop genre by demographic (minimum ${minimumRatings} ratings)`);
console.table(rows);
