const express = require('express');
const app = express();
const server = require('http').createServer(app); 
const path = require('path');
const multer = require('multer');
const pug = require('pug');
const basicAuth = require('express-basic-auth');
const sqlite3 = require('sqlite3').verbose();

// Configure the rendering engine and static folder
app.set('view engine', 'pug');
app.use("/uploads", express.static(path.join(__dirname, 'uploads')));

// Setup the database
const db = new sqlite3.Database('./project.db');

// Create the database tables
db.serialize(function() {  
    db.run("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, UNIQUE(email))");
    db.run("CREATE TABLE IF NOT EXISTS health_data (id INTEGER PRIMARY KEY, user_id INTEGER, heart_rate INTEGER, image TEXT, created TEXT)");
});

// Configure file uploads
var storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, 'uploads/')
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + '-' + Math.round(Math.random() * 1E5) + '.jpg')
  }
});

// Middleware
const upload = multer({ storage: storage });
app.use(express.json());
app.use(auth);

// Basic auth middleware - all post requests must include a specifc API key
function auth(req, res, next) {
	if (req.method != 'GET') {
	    // api_key normally goes in a config file
		api_key = "cbb55f1ebc328401c04941968b597b0b"; 
		try {
			var key = req.headers.api_key;
			if (key != api_key) throw Error("Invalid request")
			return next();
		} catch (e) {
			res.status(401);
			res.send("Unauthorised");
		}
	} else {
		return next();
	}
}

// Configure password protection of important pages
const protectedPage = basicAuth({users: { admin: 'admin' }, challenge: true});

// Our main page
app.get('/', protectedPage, function (req, res) {
	var user_email = req.query.user;

	if (!user_email) {
		db.all("SELECT * FROM users", (error, rows) => {
		    res.render('list', { users: rows});
		});
	} else {
		var stmt = db.prepare("SELECT * FROM users WHERE email=?");
		stmt.get(user_email, function(err, row) {

			if(row != undefined) {
				var stmt_data = db.prepare("SELECT * FROM health_data WHERE user_id=?");
				stmt_data.all(row.id, (error, rows) => {

					const heart_rates = rows.map(x => x.heart_rate);
					const dates = rows.map(x => x.created);

					res.render('index', { health_data: rows, heart_rates: heart_rates, dates: dates, email: user_email });
				});
				stmt_data.finalize();
			} else {
				res.send("404 - user not found");
			}
		});
		stmt.finalize();
	}
});

// Save and sync data from the sensors
app.post('/sync', upload.single('file'), function(req, res, next) {
	var user_email = req.body.user;

	// Save the data to the database, first checking if the user exists
	db.serialize(function() {
		var stmt = db.prepare("SELECT * FROM users WHERE email=?");
		stmt.get(user_email, function(err, row) {
			if(row != undefined) {
				saveData(row.id, req.body, req.file);
			} else {
				var stmt_usr = db.prepare("INSERT INTO users (email) VALUES (?)");
				stmt_usr.run(user_email,
				    function(err) {
				        // Save sensor data in the database
				        saveData(this.lastID, req.body, req.file);
				    }
				);
				stmt_usr.finalize();
			}
		});
		stmt.finalize();
	});
    res.send(true);
});

// Save sensor data
function saveData(user, body, file) {
	var stmt = db.prepare("INSERT INTO health_data (user_id, heart_rate, image, created) VALUES (?,?,?, CURRENT_TIMESTAMP)");
	stmt.run(user, body.hr, file.filename);
	stmt.finalize();
}

//start the web server
server.listen(); 