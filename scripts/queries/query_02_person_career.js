// Run: make query-2 PERSON_NAME="Christopher Nolan"
const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
const personName = process.env.PERSON_NAME || "Christopher Nolan";
database.personCredits.aggregate([
  {$match: {personName, roleName: {$in: ["Actor", "Director"]}}},
  {$group: {_id: {personId: "$personId", movieId: "$movieId"}, personName: {$first: "$personName"}, movieTitle: {$first: "$movieTitle"}, roles: {$addToSet: "$roleName"}, revenue: {$first: "$movieStats.revenue"}}},
  {$group: {_id: "$_id.personId", personName: {$first: "$personName"}, movies: {$push: {title: "$movieTitle", roles: "$roles", revenue: "$revenue"}}, totalRevenue: {$sum: "$revenue"}}},
  {$project: {_id: 0, personName: 1, movies: 1, totalRevenue: 1}},
], {allowDiskUse: true}).forEach(printjson);
