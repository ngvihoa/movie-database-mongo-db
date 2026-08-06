const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");

function summarizeExplain(explain) {
  const candidates = [];
  const indexes = new Set();
  const stages = new Set();

  function visit(value) {
    if (!value || typeof value !== "object") return;
    if (value.executionStats) candidates.push(value.executionStats);
    if (value.totalDocsExamined !== undefined && value.executionTimeMillis !== undefined) {
      candidates.push(value);
    }
    if (value.indexName) indexes.add(value.indexName);
    if (typeof value.stage === "string") stages.add(value.stage);
    for (const child of Object.values(value)) visit(child);
  }
  visit(explain);
  candidates.sort((left, right) =>
    (right.totalDocsExamined || 0) - (left.totalDocsExamined || 0)
  );
  const stats = candidates[0] || {};
  return {
    executionTimeMillis: stats.executionTimeMillis ?? null,
    nReturned: stats.nReturned ?? null,
    totalDocsExamined: stats.totalDocsExamined ?? null,
    totalKeysExamined: stats.totalKeysExamined ?? null,
    indexes: [...indexes].sort(),
    stages: [...stages].sort(),
  };
}

function benchmarkAggregate(name, collection, pipeline, options = {}) {
  const startedAt = Date.now();
  const resultCount = database[collection].aggregate(pipeline, options).toArray().length;
  const elapsedMillis = Date.now() - startedAt;
  const explain = database[collection].explain("executionStats").aggregate(pipeline, options);
  return {name, collection, resultCount, elapsedMillis, ...summarizeExplain(explain)};
}

const actionPipeline = [
  {$match: {"genres.genreName": "Action", "ratingStats.ratingCount": {$gte: 50}}},
  {$sort: {"ratingStats.averageRating": -1, "ratingStats.ratingCount": -1}},
  {$limit: 10},
  {$project: {_id: 0, title: 1, averageRating: "$ratingStats.averageRating", ratingCount: "$ratingStats.ratingCount"}},
];

const personCareerPipeline = [
  {$match: {personName: "Christopher Nolan"}},
  {$lookup: {from: "personCredits", localField: "_id", foreignField: "personId", as: "credit"}},
  {$unwind: "$credit"},
  {$match: {"credit.roleName": {$in: ["Actor", "Director"]}}},
  {$group: {_id: {personId: "$_id", movieId: "$credit.movieId"}, personName: {$first: "$personName"}, roles: {$addToSet: "$credit.roleName"}}},
  {$lookup: {from: "movies", localField: "_id.movieId", foreignField: "_id", as: "movie"}},
  {$set: {movie: {$first: "$movie"}}},
  {$group: {_id: "$_id.personId", personName: {$first: "$personName"}, movies: {$push: {title: "$movie.title", roles: "$roles", revenue: {$ifNull: ["$movie.revenue", 0]}}}, totalRevenue: {$sum: {$ifNull: ["$movie.revenue", 0]}}}},
  {$project: {_id: 0, personName: 1, movies: 1, totalRevenue: 1}},
];

function rankingPipeline(role) {
  return [
    {$match: {roleName: role}},
    {$group: {_id: {personId: "$personId", movieId: "$movieId"}}},
    {$lookup: {from: "movies", localField: "_id.movieId", foreignField: "_id", as: "movie"}},
    {$set: {movie: {$first: "$movie"}}},
    {$group: {_id: "$_id.personId", movieCount: {$sum: 1}, averageMovieRating: {$avg: {$cond: [{$gt: [{$ifNull: ["$movie.ratingStats.ratingCount", 0]}, 0]}, "$movie.ratingStats.averageRating", null]}}}},
    {$lookup: {from: "people", localField: "_id", foreignField: "_id", as: "person"}},
    {$set: {person: {$first: "$person"}}},
    {$sort: {movieCount: -1, averageMovieRating: -1}},
    {$limit: 10},
    {$project: {_id: 0, personName: "$person.personName", movieCount: 1, averageMovieRating: {$round: ["$averageMovieRating", 4]}}},
  ];
}

const demographicPipeline = [
  {$unwind: "$movieSnapshot.genres"},
  {$group: {_id: {country: "$userSnapshot.country", ageGroup: "$userSnapshot.ageGroup", genreId: "$movieSnapshot.genres.genreId"}, genreName: {$first: "$movieSnapshot.genres.genreName"}, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}},
  {$match: {ratingCount: {$gte: 20}}},
  {$sort: {"_id.country": 1, "_id.ageGroup": 1, averageRating: -1, ratingCount: -1}},
  {$group: {_id: {country: "$_id.country", ageGroup: "$_id.ageGroup"}, topGenre: {$first: "$genreName"}, averageRating: {$first: "$averageRating"}, ratingCount: {$first: "$ratingCount"}}},
  {$project: {_id: 0, country: "$_id.country", ageGroup: "$_id.ageGroup", topGenre: 1, averageRating: 1, ratingCount: 1}},
  {$sort: {country: 1, ageGroup: 1}},
];

const countryAgePipeline = [
  {$match: {"movieSnapshot.genres.genreName": "Action"}},
  {$facet: {
    detail: [{$group: {_id: {country: "$userSnapshot.country", ageGroup: "$userSnapshot.ageGroup"}, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}],
    countrySubtotal: [{$group: {_id: "$userSnapshot.country", ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}],
    grandTotal: [{$group: {_id: null, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}],
  }},
];

const topGenres = database.movies.aggregate([
  {$unwind: "$genres"},
  {$group: {_id: "$genres.genreName", totalRevenue: {$sum: "$revenue"}}},
  {$sort: {totalRevenue: -1}}, {$limit: 5},
]).toArray().map(item => item._id);
const companyPipeline = [
  {$unwind: "$companies"},
  {$group: {_id: "$companies.companyId", companyName: {$first: "$companies.companyName"}, totalBudget: {$sum: {$ifNull: ["$budget", 0]}}, totalRevenue: {$sum: {$ifNull: ["$revenue", 0]}}, movies: {$push: {genres: "$genres", budget: {$ifNull: ["$budget", 0]}, revenue: {$ifNull: ["$revenue", 0]}}}}},
  {$match: {totalRevenue: {$gt: 1000000000}, totalBudget: {$gt: 0}}},
  {$unwind: "$movies"}, {$unwind: "$movies.genres"},
  {$match: {"movies.genres.genreName": {$in: topGenres}}},
  {$group: {_id: {companyId: "$_id", genreName: "$movies.genres.genreName"}, companyName: {$first: "$companyName"}, companyBudget: {$first: "$totalBudget"}, companyRevenue: {$first: "$totalRevenue"}, genreBudget: {$sum: "$movies.budget"}, genreRevenue: {$sum: "$movies.revenue"}}},
  {$group: {_id: "$_id.companyId", companyName: {$first: "$companyName"}, totalBudget: {$first: "$companyBudget"}, totalRevenue: {$first: "$companyRevenue"}, genreRatios: {$push: {k: "$_id.genreName", v: {$cond: [{$gt: ["$genreBudget", 0]}, {$divide: ["$genreRevenue", "$genreBudget"]}, null]}}}}},
  {$project: {_id: 0, companyName: 1, genreRatios: {$arrayToObject: "$genreRatios"}, overallRevenueBudgetRatio: {$round: [{$divide: ["$totalRevenue", "$totalBudget"]}, 4]}}},
  {$sort: {overallRevenueBudgetRatio: -1}}, {$limit: 5},
];

const results = [
  benchmarkAggregate("Q1 Top Action movies", "movies", actionPipeline),
  benchmarkAggregate("Q2 Person career", "people", personCareerPipeline, {allowDiskUse: true}),
  benchmarkAggregate("Q3 Actor ranking", "personCredits", rankingPipeline("Actor"), {allowDiskUse: true}),
  benchmarkAggregate("Q3 Director ranking", "personCredits", rankingPipeline("Director"), {allowDiskUse: true}),
  benchmarkAggregate("Q4 Top genre by demographic", "ratings", demographicPipeline, {allowDiskUse: true}),
  benchmarkAggregate("Q5 Country and age report", "ratings", countryAgePipeline, {allowDiskUse: true}),
  benchmarkAggregate("Q6 Company investment", "movies", companyPipeline, {allowDiskUse: true}),
];

print(JSON.stringify({generatedAt: new Date(), database: database.getName(), topGenresForQ6: topGenres, results}, null, 2));
