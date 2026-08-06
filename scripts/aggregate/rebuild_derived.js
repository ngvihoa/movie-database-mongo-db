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

database.companies.updateMany({}, {$unset: {companyStats: "", statsUpdatedAt: ""}});

print("Movie rating statistics rebuilt.");
