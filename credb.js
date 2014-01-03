/*

// login
$ mongo
show dbs
use your_database_name
show collections

// drop database
use your_database_name
db.dropDatabase()

// drop collection
db.response.drop()
db.live.drop()
db.news.drop()
db.video.drop()

*/

// drop before create
db.dropDatabase()

// create index
db.response.ensureIndex({community:1, number:1})
db.response.ensureIndex({community:1, status:1})
db.live.ensureIndex({community:1, link:1})
db.live.ensureIndex({community:1, status:1})
db.news.ensureIndex({community:1, date:1})
db.news.ensureIndex({community:1, status:1})
db.video.ensureIndex({community:1, link:1})
db.video.ensureIndex({community:1, status:1})

/*
// print content
db.response.find().forEach(function(x){printjson(x);})
db.live.find().forEach(function(x){printjson(x);})
db.news.find().forEach(function(x){printjson(x);})
db.video.find().forEach(function(x){printjson(x);})

// print index
db.response.getIndexes().forEach(function(x){printjson(x);})
db.live.getIndexes().forEach(function(x){printjson(x);})
db.news.getIndexes().forEach(function(x){printjson(x);})
db.video.getIndexes().forEach(function(x){printjson(x);})
*/
