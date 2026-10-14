var express = require('express');
var router = express.Router();
const pgp = require("pg-promise")(/* options */);
const PG_CONNECT_STR = process.env["POSTGRESQL_DB_CONNECT_STRING"];

/* GET home page. */
router.get('/', async function(req, res, next) {
  console.log("new hello world request");

  if (!PG_CONNECT_STR) {
    console.error("Database connection string is not set");
    return res.status(500).send("Database connection error");
  }

  const db = pgp(PG_CONNECT_STR);

  try {
    const userAgent = req.get("User-Agent");
    const timestamp = new Date();

    await db.none(
      "INSERT INTO visitors (timestamp, user_agent) VALUES ($1, $2)",
      [timestamp, userAgent]
    );

    const greeting = process.env["APP_GREETING"] || "Hello, world!";
    res.send(greeting + "\n");
  } catch (error) {
    console.error("An error occurred:", error);
    res.status(500).send("An error occurred while processing your request");
  } finally {
    db.$pool.end(); // Close the database connection pool
  }
});

module.exports = router;
