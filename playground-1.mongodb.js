use("movie_analytics");

db.movies.find({
  "genres.genreName": "Action",
});
