// Run: make query-2 PERSON_NAME="Christopher Nolan"
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const personName = process.env.PERSON_NAME || "Christopher Nolan";
const people = database.people
  .aggregate(
    [
      { $match: { personName } },
      {
        $lookup: {
          from: "personCredits",
          localField: "_id",
          foreignField: "personId",
          as: "credit",
        },
      },
      { $unwind: "$credit" },
      { $match: { "credit.roleName": { $in: ["Actor", "Director"] } } },
      {
        $group: {
          _id: { personId: "$_id", movieId: "$credit.movieId" },
          personName: { $first: "$personName" },
          roles: { $addToSet: "$credit.roleName" },
        },
      },
      {
        $lookup: {
          from: "movies",
          localField: "_id.movieId",
          foreignField: "_id",
          as: "movie",
        },
      },
      { $set: { movie: { $first: "$movie" } } },
      {
        $group: {
          _id: "$_id.personId",
          personName: { $first: "$personName" },
          movies: {
            $push: {
              title: "$movie.title",
              roles: "$roles",
              revenue: { $ifNull: ["$movie.revenue", 0] },
            },
          },
          totalRevenue: { $sum: { $ifNull: ["$movie.revenue", 0] } },
        },
      },
      { $project: { _id: 0, personName: 1, movies: 1, totalRevenue: 1 } },
    ],
    { allowDiskUse: true },
  )
  .toArray();

if (people.length === 0) {
  console.log(`\nNo Actor or Director credits found for "${personName}".`);
}

people.forEach((person) => {
  console.log(`\nCareer summary: ${person.personName}`);
  console.table([
    {
      personName: person.personName,
      movieCount: person.movies.length,
      totalRevenue: person.totalRevenue,
    },
  ]);
  console.log("Movies");
  console.table(
    person.movies.map((movie) => ({
      title: movie.title,
      roles: movie.roles.join(", "),
      revenue: movie.revenue,
    })),
  );
});
