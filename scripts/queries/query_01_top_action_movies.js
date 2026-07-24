// Run: mongosh "$MONGODB_URI/$MONGODB_DATABASE" scripts/queries/query_01_top_action_movies.js
const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
database.movies.find(
  {"genres.genreName": "Action", "ratingStats.ratingCount": {$gte: 50}},
  {_id: 0, title: 1, averageRating: "$ratingStats.averageRating", ratingCount: "$ratingStats.ratingCount"},
).sort({"ratingStats.averageRating": -1, "ratingStats.ratingCount": -1}).limit(10).forEach(printjson);
