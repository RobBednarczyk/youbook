# Youbook 1.1
**Create your bookshelves and show it to the world!**

# General Info
The Youbook application lets users create bookshelves with their favourite books
and show it to other users.

# Installation
Youbook application requires a Python environment with the following libraries:
- sqlalchemy
- flask
- passlib
- oauth2client.client

Once the *bookshelves* folder has beed downloaded the user needs to access it:

```sh
$ cd /bookshelves
```
and launch the server:

```sh
$ python views.py
```

The application will then be accessible under the urls:
http://localhost:5000
or
http://localhost:5000/bookshelves

# User guide
The first thing a user should do is to log into the system. This can be done
in two ways:

- using the internal login procedure (users are expected to provide their
  username, password and an optional url to a photo)

- using the third party login service providers such as Google+ or Facebook
  (the links will be visible on the login page)

**Warning: only the registered users can add, edit and delete books and bookshelves**

# APIs endpoints

The following API data is provided to developers:

- user data ("/users/json")

```sh
{
  "users": [
    {
      "image": "https://goo.gl/9HnqeB",
      "user_id": 1,
      "username": "Dexter"
    },
    {
      "image": "https://goo.gl/FvmAb4",
      "user_id": 2,
      "username": "Adam Jensen"
    }
  ]
}
```

- bookshelves data ("/bookshelves/json")

```sh
{
  "bookshelves": [
    {
      "bookshelf_id": 1,
      "bookshelf_image": image_url,
      "bookshelf_name": name
    },
    {
      "bookshelf_id": 2,
      "bookshelf_image": image_url,
      "bookshelf_name": name
    }
  ]
}
```
- book data ("/bookshelves/<bookshelf_id>/json")

```sh
{
  "bookshelfBooks": [
    {
      "author": author,
      "book_id": 1,
      "category": category,
      "title": title
    },
    {
      "author": author,
      "book_id": 2,
      "category": category,
      "title": title
    }
  ]
}
```

# Ending remarks
Developed by Robert Bednarczyk.
The creator of the app does not own nor claim rights to any image posted in the
app system.
