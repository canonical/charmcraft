var express = require('express');
var router = express.Router();

let greeting = process.env["APP_GREETING"]

if (!greeting){
  greeting = "Hello, world!";
}

/* GET home page. */
router.get('/', function(req, res, next) {
  res.send(greeting);
});

module.exports = router;
