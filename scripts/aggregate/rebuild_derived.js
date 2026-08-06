const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
const now = new Date();

database.ratings.aggregate([
  {$group: {_id: "$movieId", ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}},
  {$project: {_id: 1, ratingStats: {ratingCount: "$ratingCount", averageRating: {$round: ["$averageRating", 4]}}, ratingStatsUpdatedAt: now}},
  {$merge: {into: "movies", on: "_id", whenMatched: [{$set: {ratingStats: "$$new.ratingStats", ratingStatsUpdatedAt: "$$new.ratingStatsUpdatedAt"}}], whenNotMatched: "discard"}},
], {allowDiskUse: true});

database.people.updateMany({}, {$unset: {careerStats: "", statsUpdatedAt: ""}});
database.personCredits.updateMany(
  {},
  {$unset: {personName: "", movieTitle: "", movieStats: ""}},
);

database.companyMovies.deleteMany({});
database.movies.aggregate([
  {$unwind: "$companies"},
  {$project: {_id: 0, companyId: "$companies.companyId", companyName: "$companies.companyName", movieId: "$_id", movieTitle: "$title", financials: {budget: "$budget", revenue: "$revenue", revenueBudgetRatio: {$cond: [{$gt: ["$budget", 0]}, {$divide: ["$revenue", "$budget"]}, null]}}, genres: 1, ratingStats: 1, createdAt: now, updatedAt: now}},
  {$merge: {into: "companyMovies", on: ["companyId", "movieId"], whenMatched: "replace", whenNotMatched: "insert"}},
], {allowDiskUse: true});

database.companyMovies.aggregate([
  {$group: {_id: "$companyId", movieCount: {$sum: 1}, totalBudget: {$sum: "$financials.budget"}, totalRevenue: {$sum: "$financials.revenue"}}},
  {$project: {_id: 1, companyStats: {movieCount: "$movieCount", totalBudget: "$totalBudget", totalRevenue: "$totalRevenue", revenueBudgetRatio: {$cond: [{$gt: ["$totalBudget", 0]}, {$divide: ["$totalRevenue", "$totalBudget"]}, null]}}, statsUpdatedAt: now}},
  {$merge: {into: "companies", on: "_id", whenMatched: [{$set: {companyStats: "$$new.companyStats", statsUpdatedAt: "$$new.statsUpdatedAt"}}], whenNotMatched: "discard"}},
], {allowDiskUse: true});

database.demographicGenreStats.deleteMany({});
database.ratings.aggregate([
  {$unwind: "$movieSnapshot.genres"},
  {$group: {_id: {genreId: "$movieSnapshot.genres.genreId", country: "$userSnapshot.country", ageGroup: "$userSnapshot.ageGroup"}, genreName: {$first: "$movieSnapshot.genres.genreName"}, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}},
  {$project: {_id: 0, genreId: "$_id.genreId", genreName: 1, country: "$_id.country", ageGroup: "$_id.ageGroup", ratingCount: 1, averageRating: {$round: ["$averageRating", 4]}, calculatedAt: now}},
  {$merge: {into: "demographicGenreStats", on: ["genreId", "country", "ageGroup"], whenMatched: "replace", whenNotMatched: "insert"}},
], {allowDiskUse: true});

database.companyGenreStats.deleteMany({});
database.companyMovies.aggregate([
  {$unwind: "$genres"},
  {$group: {_id: {companyId: "$companyId", genreId: "$genres.genreId"}, companyName: {$first: "$companyName"}, genreName: {$first: "$genres.genreName"}, movieCount: {$sum: 1}, totalBudget: {$sum: "$financials.budget"}, totalRevenue: {$sum: "$financials.revenue"}, averageMovieRevenueBudgetRatio: {$avg: "$financials.revenueBudgetRatio"}}},
  {$project: {_id: 0, companyId: "$_id.companyId", companyName: 1, genreId: "$_id.genreId", genreName: 1, movieCount: 1, totalBudget: 1, totalRevenue: 1, averageMovieRevenueBudgetRatio: {$round: ["$averageMovieRevenueBudgetRatio", 4]}, overallRevenueBudgetRatio: {$cond: [{$gt: ["$totalBudget", 0]}, {$round: [{$divide: ["$totalRevenue", "$totalBudget"]}, 4]}, null]}, calculatedAt: now}},
  {$merge: {into: "companyGenreStats", on: ["companyId", "genreId"], whenMatched: "replace", whenNotMatched: "insert"}},
], {allowDiskUse: true});

print("Derived collections and statistics rebuilt.");
