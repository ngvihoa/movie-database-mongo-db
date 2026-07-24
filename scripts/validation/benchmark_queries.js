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
  {$match: {personName: "Christopher Nolan", roleName: {$in: ["Actor", "Director"]}}},
  {$group: {_id: {personId: "$personId", movieId: "$movieId"}, personName: {$first: "$personName"}, movieTitle: {$first: "$movieTitle"}, roles: {$addToSet: "$roleName"}, revenue: {$first: "$movieStats.revenue"}}},
  {$group: {_id: "$_id.personId", personName: {$first: "$personName"}, movies: {$push: {title: "$movieTitle", roles: "$roles", revenue: "$revenue"}}, totalRevenue: {$sum: "$revenue"}}},
  {$project: {_id: 0, personName: 1, movies: 1, totalRevenue: 1}},
];

const actorRankingPipeline = [
  {$match: {"careerStats.actorMovieCount": {$gt: 0}}},
  {$sort: {"careerStats.actorMovieCount": -1, "careerStats.actorAverageMovieRating": -1}},
  {$limit: 10},
  {$project: {_id: 0, personName: 1, movieCount: "$careerStats.actorMovieCount", averageMovieRating: "$careerStats.actorAverageMovieRating"}},
];

const directorRankingPipeline = [
  {$match: {"careerStats.directorMovieCount": {$gt: 0}}},
  {$sort: {"careerStats.directorMovieCount": -1, "careerStats.directorAverageMovieRating": -1}},
  {$limit: 10},
  {$project: {_id: 0, personName: 1, movieCount: "$careerStats.directorMovieCount", averageMovieRating: "$careerStats.directorAverageMovieRating"}},
];

const demographicPipeline = [
  {$match: {ratingCount: {$gte: 20}}},
  {$sort: {country: 1, ageGroup: 1, averageRating: -1, ratingCount: -1}},
  {$group: {_id: {country: "$country", ageGroup: "$ageGroup"}, topGenre: {$first: "$genreName"}, averageRating: {$first: "$averageRating"}, ratingCount: {$first: "$ratingCount"}}},
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
  {$match: {genreName: {$in: topGenres}}},
  {$group: {_id: "$companyId", companyName: {$first: "$companyName"}, genreRatios: {$push: {k: "$genreName", v: "$overallRevenueBudgetRatio"}}}},
  {$lookup: {from: "companies", localField: "_id", foreignField: "_id", as: "company"}},
  {$set: {company: {$first: "$company"}}},
  {$match: {"company.companyStats.totalRevenue": {$gt: 1000000000}, "company.companyStats.totalBudget": {$gt: 0}}},
  {$project: {_id: 0, companyName: 1, genreRatios: {$arrayToObject: "$genreRatios"}, overallRevenueBudgetRatio: {$round: ["$company.companyStats.revenueBudgetRatio", 4]}}},
  {$sort: {overallRevenueBudgetRatio: -1}}, {$limit: 5},
];

const results = [
  benchmarkAggregate("Q1 Top Action movies", "movies", actionPipeline),
  benchmarkAggregate("Q2 Person career", "personCredits", personCareerPipeline, {allowDiskUse: true}),
  benchmarkAggregate("Q3 Actor ranking", "people", actorRankingPipeline),
  benchmarkAggregate("Q3 Director ranking", "people", directorRankingPipeline),
  benchmarkAggregate("Q4 Top genre by demographic", "demographicGenreStats", demographicPipeline),
  benchmarkAggregate("Q5 Country and age report", "ratings", countryAgePipeline, {allowDiskUse: true}),
  benchmarkAggregate("Q6 Company investment", "companyGenreStats", companyPipeline, {allowDiskUse: true}),
];

print(JSON.stringify({generatedAt: new Date(), database: database.getName(), topGenresForQ6: topGenres, results}, null, 2));
