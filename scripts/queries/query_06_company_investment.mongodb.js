// Run: make query-6
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const topGenres = database.movies
  .aggregate([
    { $unwind: "$genres" },
    {
      $group: { _id: "$genres.genreName", totalRevenue: { $sum: "$revenue" } },
    },
    { $sort: { totalRevenue: -1 } },
    { $limit: 5 },
  ])
  .toArray()
  .map((item) => item._id);
const companies = database.movies
  .aggregate(
    [
      { $unwind: "$companies" },
      {
        $group: {
          _id: "$companies.companyId",
          companyName: { $first: "$companies.companyName" },
          totalBudget: { $sum: { $ifNull: ["$budget", 0] } },
          totalRevenue: { $sum: { $ifNull: ["$revenue", 0] } },
          movies: {
            $push: {
              genres: "$genres",
              budget: { $ifNull: ["$budget", 0] },
              revenue: { $ifNull: ["$revenue", 0] },
            },
          },
        },
      },
      { $match: { totalRevenue: { $gt: 1000000000 }, totalBudget: { $gt: 0 } } },
      { $unwind: "$movies" },
      { $unwind: "$movies.genres" },
      { $match: { "movies.genres.genreName": { $in: topGenres } } },
      {
        $group: {
          _id: { companyId: "$_id", genreName: "$movies.genres.genreName" },
          companyName: { $first: "$companyName" },
          companyBudget: { $first: "$totalBudget" },
          companyRevenue: { $first: "$totalRevenue" },
          movieCount: { $sum: 1 },
          genreBudget: { $sum: "$movies.budget" },
          genreRevenue: { $sum: "$movies.revenue" },
        },
      },
      {
        $group: {
          _id: "$_id.companyId",
          companyName: { $first: "$companyName" },
          totalBudget: { $first: "$companyBudget" },
          totalRevenue: { $first: "$companyRevenue" },
          genreStats: {
            $push: {
              k: "$_id.genreName",
              v: {
                movieCount: "$movieCount",
                totalBudget: "$genreBudget",
                ratio: {
                  $cond: [
                    { $gt: ["$genreBudget", 0] },
                    { $round: [{ $divide: ["$genreRevenue", "$genreBudget"] }, 4] },
                    null,
                  ],
                },
              },
            },
          },
        },
      },
      {
        $project: {
          _id: 0,
          companyName: 1,
          genreStats: { $arrayToObject: "$genreStats" },
          overallRevenueBudgetRatio: {
            $round: [{ $divide: ["$totalRevenue", "$totalBudget"] }, 4],
          },
        },
      },
      { $sort: { overallRevenueBudgetRatio: -1 } },
      { $limit: 5 },
    ],
    { allowDiskUse: true },
  )
  .toArray();

console.log(`\nTop revenue genres: ${topGenres.join(", ")}`);
console.log("Top 5 companies by overall revenue/budget ratio");
console.table(
  companies.map((company) => ({
    companyName: company.companyName,
    overallRatio: company.overallRevenueBudgetRatio,
    ...Object.fromEntries(
      topGenres.map((genre) => {
        const stats = company.genreStats[genre];
        if (!stats) return [genre, "N/A (no movies)"];
        if (stats.totalBudget <= 0) return [genre, "N/A (missing budget)"];
        return [genre, stats.ratio];
      }),
    ),
  })),
);
