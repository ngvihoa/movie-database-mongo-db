// Run: make query-test
const database = db.getSiblingDB(
  process.env.MONGODB_DATABASE || "movie_analytics",
);

/* ----------------------------------Helper Function---------------------------------- */

function flattenDocument(document, prefix = "", row = {}) {
  Object.entries(document).forEach(([key, value]) => {
    const column = prefix ? `${prefix}.${key}` : key;
    const isPlainObject =
      value !== null &&
      !Array.isArray(value) &&
      value.constructor?.name === "Object";

    if (isPlainObject) {
      flattenDocument(value, column, row);
    } else {
      row[column] = Array.isArray(value) ? JSON.stringify(value) : value;
    }
  });
  return row;
}

function printTable(result) {
  const documents =
    typeof result?.toArray === "function"
      ? result.toArray()
      : Array.isArray(result)
        ? result
        : [result];

  if (documents.length === 0) {
    console.log("No results.");
    return;
  }

  console.table(documents.map((document) => flattenDocument(document)));
}

/* ----------------------------------Query---------------------------------- */

const result = database.personCredits.aggregate([
  {
    $group: {
      _id: "$personId",
      creditCount: { $sum: 1 },
      movieIds: { $addToSet: "$movieId" },
      roles: { $addToSet: "$roleName" }
    }
  },
  {
    $lookup: {
      from: "people",
      localField: "_id",
      foreignField: "_id",
      as: "person"
    }
  },
  { $set: { personName: { $first: "$person.personName" } } },
  {
    $project: {
      _id: 0,
      personName: 1,
      creditCount: 1,
      movieCount: { $size: "$movieIds" },
      roles: 1
    }
  },
  { $sort: { creditCount: -1 } },
  { $limit: 20 }
]);
printTable(result);
