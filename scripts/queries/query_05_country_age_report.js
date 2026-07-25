// Run: make query-5 GENRE_NAME="Action"
const database = db.getSiblingDB(process.env.MONGODB_DATABASE || "movie_analytics");
const genreName = process.env.GENRE_NAME || "Action";
const rows = database.ratings.aggregate([
  {$match: {"movieSnapshot.genres.genreName": genreName}},
  {$facet: {
    detail: [{$group: {_id: {country: "$userSnapshot.country", ageGroup: "$userSnapshot.ageGroup"}, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}, {$project: {_id: 0, level: "AGE_GROUP", sortCountry: "$_id.country", sortOrder: {$literal: 1}, country: "$_id.country", ageGroup: "$_id.ageGroup", ratingCount: 1, averageRating: {$round: ["$averageRating", 4]}}}],
    countrySubtotal: [{$group: {_id: "$userSnapshot.country", ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}, {$project: {_id: 0, level: "COUNTRY_SUBTOTAL", sortCountry: "$_id", sortOrder: {$literal: 2}, country: "$_id", ageGroup: null, ratingCount: 1, averageRating: {$round: ["$averageRating", 4]}}}],
    grandTotal: [{$group: {_id: null, ratingCount: {$sum: 1}, averageRating: {$avg: "$rating"}}}, {$project: {_id: 0, level: "GRAND_TOTAL", sortCountry: "~~~~", sortOrder: {$literal: 3}, country: null, ageGroup: null, ratingCount: 1, averageRating: {$round: ["$averageRating", 4]}}}],
  }},
  {$project: {rows: {$concatArrays: ["$detail", "$countrySubtotal", "$grandTotal"]}}},
  {$unwind: "$rows"}, {$replaceWith: "$rows"},
  {$sort: {sortCountry: 1, sortOrder: 1, ageGroup: 1}},
  {$unset: ["sortCountry", "sortOrder"]},
], {allowDiskUse: true}).toArray();
printjson({genreName, hierarchy: "Country -> Age group -> Country subtotal -> Grand total", rows});
