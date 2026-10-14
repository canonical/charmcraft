var express = require("express");
var router = express.Router();
const pgp = require("pg-promise")(/* options */);
const PG_CONNECT_STR = process.env["POSTGRESQL_DB_CONNECT_STRING"];

console.log("PG_CONNECT_STR", PG_CONNECT_STR);
let db = null;

if (PG_CONNECT_STR) {
  db = pgp(PG_CONNECT_STR);
}
/* GET visitors count. */
router.get("/", async function (req, res, next) {
  console.log("visitors request");

  if (!db) {
    console.error("Database connection is not initialized");
    return res.status(500).send("Database connection error");
  }

  try {
    const result = await db.one("SELECT count(*) FROM visitors");
    const numVisitors = result.count;

    res.send(`Number of visitors: ${numVisitors}\n`);
  } catch (error) {
    console.error("An error occurred while executing query:", error);
    res.status(500).send("Error retrieving visitors count");
  }
});

module.exports = router;
