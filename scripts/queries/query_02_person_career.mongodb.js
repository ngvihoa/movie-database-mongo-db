// Run: make query-2 PERSON_NAME="Christopher Nolan"
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);
const personName = process.env.PERSON_NAME || "Christopher Nolan";
const people = database.personCredits
  .aggregate(
    [
      { $match: { personName, roleName: { $in: ["Actor", "Director"] } } },
      {
        $group: {
          _id: { personId: "$personId", movieId: "$movieId" },
          personName: { $first: "$personName" },
          movieTitle: { $first: "$movieTitle" },
          roles: { $addToSet: "$roleName" },
          revenue: { $first: "$movieStats.revenue" },
        },
      },
      {
        $group: {
          _id: "$_id.personId",
          personName: { $first: "$personName" },
          movies: {
            $push: {
              title: "$movieTitle",
              roles: "$roles",
              revenue: "$revenue",
            },
          },
          totalRevenue: { $sum: "$revenue" },
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
