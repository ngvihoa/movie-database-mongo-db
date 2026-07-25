// Run: make query-6
const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
const topGenres = database.movies.aggregate([
  {$unwind: "$genres"},
  {$group: {_id: "$genres.genreName", totalRevenue: {$sum: "$revenue"}}},
  {$sort: {totalRevenue: -1}}, {$limit: 5},
]).toArray().map(item => item._id);
const companies = database.companyGenreStats.aggregate([
  {$match: {genreName: {$in: topGenres}}},
  {$group: {_id: "$companyId", companyName: {$first: "$companyName"}, genreRatios: {$push: {k: "$genreName", v: "$overallRevenueBudgetRatio"}}}},
  {$lookup: {from: "companies", localField: "_id", foreignField: "_id", as: "company"}},
  {$set: {company: {$first: "$company"}}},
  {$match: {"company.companyStats.totalRevenue": {$gt: 1000000000}, "company.companyStats.totalBudget": {$gt: 0}}},
  {$project: {_id: 0, companyName: 1, genreRatios: {$arrayToObject: "$genreRatios"}, overallRevenueBudgetRatio: {$round: ["$company.companyStats.revenueBudgetRatio", 4]}}},
  {$sort: {overallRevenueBudgetRatio: -1}}, {$limit: 5},
], {allowDiskUse: true}).toArray();
printjson({topRevenueGenres: topGenres, companies});
