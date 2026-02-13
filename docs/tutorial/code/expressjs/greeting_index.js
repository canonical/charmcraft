var express = require('express');
var router = express.Router();

let greeting = process.env["APP_GREETING"]

/* GET home page. */
router.get('/', function(req, res, next) {
  res.send(greeting);
});

module.exports = router;
