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

const result = database.users.find().limit(10);
printTable(result);
