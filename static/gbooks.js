function loadData(e) {
	e.preventDefault()
	//console.log("Welcome!");
	var $body = $("body");
	var $gbooksHeader = $("#gbooks-header");
	var $gbooks = $("#gbooks-items")

	$gbooksHeader.text("Relevant books from Google Books service");
	// clear the old data
	$gbooks.text("");

	// extract the data provided by the user

	var phrase = $("#phrase").val();
	var title = $("#title").val();
	var author = $("#author").val();
	var subject = $("#subject").val();

	// gbooks API endpoint
	var gbooksURL = "https://www.googleapis.com/books/v1/volumes?q=";

	if (!phrase) {
		window.alert("Please fill in at least the searched phrase.");
		console.log("Please fill in at least the searched phrase.");
		return;
	} else {
		var gbooksURL = gbooksURL + phrase;
	}

	if (title) {
		var gbooksURL = gbooksURL + "+intitle:" + title;
	}

	if (author) {
		var gbooksURL = gbooksURL + "+inauthor:" + author;
	}

	if (subject) {
		var gbooksURL = gbooksURL + "+insubject:" + subject;
	}
	//} else if (author) {
	//	var gbooksURL = gbooksURL + "+inauthor:" + author;
	//} else if (subject) {
	//	var gbooksURL = gbooksURL + "+insubject:" + subject;
	//}

	var gbooksURL = gbooksURL + "&maxResults=20";

	//console.log(gbooksURL);
	$.getJSON(gbooksURL, function(data) {
		console.log(data["items"]);
		if (data["items"]) {

			var parameters = [];
			$.each(data["items"], function(index, value) {
				if (value["searchInfo"] && value["searchInfo"]["textSnippet"]) {
					var snippet = value["searchInfo"]["textSnippet"];
				} else {
					var snippet = "Snippet not available";
				}
				if (value["volumeInfo"] && value["volumeInfo"]["title"]) {
					var title = value["volumeInfo"]["title"];
				} else {
					var title = "Title not available"
				}
				if (value["volumeInfo"] && value["volumeInfo"]["authors"]) {
					var author = value["volumeInfo"]["authors"][0];
				} else {
					var author = "Author not available"
				}
				if (value["volumeInfo"] && value["volumeInfo"]["imageLinks"] && value["volumeInfo"]["imageLinks"]["thumbnail"]) {
					var imageURL = value["volumeInfo"]["imageLinks"]["thumbnail"];
				} else {
					var imageURL = "Image not available";
				}
				if (value["volumeInfo"] && value["volumeInfo"]["description"]) {
					var description = value["volumeInfo"]["description"];
				} else {
					var description = "Description not available";
				}

				if (value["volumeInfo"] && value["volumeInfo"]["categories"]) {
					var category = value["volumeInfo"]["categories"][0];
				} else {
					var category = "Category not available";
				}

				if (value["volumeInfo"]) {
					var publisher = value["volumeInfo"]["publisher"];
				} else {
					var publisher = "Publisher not available";
				}


				var itemHTML = "<li class='book'><img src='" + imageURL + "'>" + "<p>" + title + "</p>" +
				"<p>" + imageURL + "</p>" +
				"<p>" + author + "</p>" + "<p class='textSnippet'>" + snippet + "</p>" + "<p>" +
				category + "</p>" + "<p>" + publisher + "</p>" +
				"<p>" + description + "</p>" +
				"<div id='addButton" + index + "'><button>Add book</button></div>" +
				"<div class='temp'></div>";

				var postData = {
				"title": title,
				"author": author,
				"image": imageURL,
				"description": description,
				"category": category,
				"publisher": publisher
				};



				parameters.push(postData)

				$gbooks.append(itemHTML);
			});

			var dataLen = parameters.length;
			alert(dataLen);
			for (i = 0; i < dataLen; i++) {
				var elName = "#addButton" + i
				//alert(elName);
				console.log(parameters[i]["author"]);
				$(elName).on("click",{params: parameters, index: i}, function(event) {
					if (confirm("Are you sure to save this book in the database?")) {
						alert("Request sent to the database");
						alert(event.data.params[event.data.index]["author"]);
						$.post("url_for('gbooksConnect', bookshelf_id = {{bookshelf_id}})",
						event.data.params[event.data.index], function() {
						});
						event.preventDefault();
					} else {
						alert("Book not saved");
					}
				});
			}

		} else {
			$gbooksHeader.text("Books could not be loaded");
		};
	});

	//}).error(function(e) {
	//	$gbooksHeader.text("Books could not be loaded");
	//});
	//

}

$('.form-container').submit(loadData);
