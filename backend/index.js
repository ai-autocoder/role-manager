const express = require("express");
const sqlite3 = require("sqlite3").verbose();

var db = new sqlite3.Database(
  "./backend/role-manager.db",
  sqlite3.OPEN_READWRITE,
  (err) => {
    if (err) return console.error(err.message);
    console.log("Connected to the SQLite database.");
  }
);

let data;

db.all("SELECT * FROM 'Users' ORDER BY Name", (err, rows) => {
  if (err) return console.error(err.message);
  data = rows;
});

db.close((err) => {
  if (err) return console.error(err.message);
  console.log("Closing the database connection.");
});

const app = express();
const PORT = process.env.PORT || 3001;

app.get("/api", (req, res) => {
  console.log(
    `Received a request from ${
      req.socket.remoteAddress
        ? req.socket.remoteAddress
        : "someone who I don't know"
    } !`
  );
  res.send({ message: data });
});

app.listen(PORT, () => {
  console.log(`Server listening on port: ${PORT}`);
});
