import random
import string
import httplib2
import json
import requests
from flask import session as login_session
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from flask import make_response
# import authorization library
from flask_httpauth import HTTPBasicAuth
# catch an error while trying to exchange the authorization
# code for an access token
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from models import Base, User, Bookshelf, Book
from flask import Flask, request, url_for, jsonify, render_template
from flask import redirect, abort, g, flash


auth = HTTPBasicAuth()

CLIENT_ID = json.loads(
    open("client_secret.json", "r").read())["web"]["client_id"]

engine = create_engine("sqlite:///bookshelvesWithUsers_v2.db")
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)


# function used to verify the user
@auth.verify_password
def verify_password(username, password):
    user = session.query(User).filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True


# GOOGLE PLUS SIGN IN FUNCTIONALITY
# Create the gconnect function
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps(
                'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    # print login_session["username"]
    login_session['image'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # check if user already exists in the database
    if getUserID(login_session["email"]):
        login_session["user_id"] = getUserID(login_session["email"])
    else:
        login_session["user_id"] = createUser(login_session)
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['image']
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: '
    output += '150px;"> '
    flash("You are now logged in as {}".format(login_session['username']))
    print "done!"
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(
            json.dumps(
                'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print "In gdisconnect access token is {}".format(access_token)
    print "User name is:"
    print login_session["username"]
    url = "https://accounts.google.com/o/oauth2/revoke?token={}".format(login_session["access_token"])
    h = httplib2.Http()
    result = h.request(url, "GET")[0]
    print "result is "
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['image']
        del login_session["user_id"]
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps(
                'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# END OF GOOGLE PLUS SIGN IN FUNCTIONALITY

# FACEBOOK SIGN IN FUNCTIONALITY
# Facebook connection part


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    print request.args.get("state")
    print login_session["state"]
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we
        have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then
        we split it on colons to pull out the actual token value and
        replace the remaining quotes with nothing so that it can be
        used directly in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['image'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['image']
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: '
    output += '150px;"> '

    flash("You are now logged in as {}".format(login_session['username']))
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = "https://graph.facebook.com/{}/permissions".format(facebook_id)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session["username"]
    del login_session["email"]
    del login_session["image"]
    del login_session["user_id"]
    del login_session["facebook_id"]
    return "You have been logged out"

# END OF FACEBOOK SIGN IN FUNCTIONALITY


# JSON APIs

@app.route("/users/json")
def usersJSON():
    users = session.query(User).all()
    return jsonify(users=[user.serialize for user in users])


@app.route("/bookshelves/json")
def bookshelvesJSON():
    bookshelves = session.query(Bookshelf).all()
    return jsonify(bookshelves=[bookshelf.serialize for bookshelf in bookshelves])


@app.route("/bookshelves/<int:bookshelf_id>/json")
def bookshelfBooksJSON(bookshelf_id):
    bookshelf = session.query(Bookshelf).get(bookshelf_id)
    books = session.query(Book).filter_by(bookshelf_id=bookshelf_id).all()
    return jsonify(bookshelfBooks=[book.serialize for book in books])


@app.route("/bookshelves/<int:bookshelf_id>/<int:book_id>/json")
def bookJSON(bookshelf_id, book_id):
    bookshelf = session.query(Bookshelf).get(bookshelf_id)
    book = session.query(Book).get(book_id)
    return jsonify(book=[book.serialize])

# END OF JSON APIs


@app.route("/users/new", methods=["GET", "POST"])
def newUser():
    if request.method == "GET":
        return render_template("newUser.html")
    elif request.method == "POST":
        username = request.form.get("newName")
        password = request.form.get("password")
        email = request.form.get("email")
        image = request.form.get("imageURL")

        if not username or not password:
            flash("Please provide both username and password.")
            return redirect(url_for("newUser"))
        user_exists = session.query(User).filter_by(username=username).first()
        if user_exists:
            flash("User already exists.")
        else:
            newUser = User(username=username)
            if image:
                newUser.user_img = image
            if email:
                newUser.email = email
            newUser.hash_password(password)
            session.add(newUser)
            flash("New user {} successfully created".format(newUser.username))
            session.commit()
            login_session["username"] = username
            login_session["email"] = email
            login_session["image"] = image
            login_session["user_id"] = newUser.id
            return redirect(url_for("displayMain_all"))


@app.route("/api/users/<int:id>")
def get_user(id):
    user = session.query(User).filter_by(id=id).one()
    if not user:
        abort(400)
    return jsonify({"username": user.username, "image": user.user_img})


@app.route("/login", methods=["GET", "POST"])
def loginPage():
    if request.method == "GET":
        # concatenate a randomly choses uppercase letter or a digit 32 times
        state = "".join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
        login_session["state"] = state
        return render_template("login.html", STATE=state)

    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            flash("Please provide the username")
            return redirect(url_for("loginPage"))
        if not password:
            flash("Please provide the password")
            return redirect(url_for("loginPage"))
        if not verify_password(username, password):
            flash("User does not exist or invalid password given")
            return redirect(url_for("loginPage"))
        else:
            login_session["username"] = username
            login_session["email"] = g.user.email
            login_session["image"] = g.user.user_img
            login_session["provider"] = "own"
            login_session["user_id"] = getUserID(login_session["email"])
            flash("You are now logged in as {}".format(login_session['username']))
            return redirect(url_for("displayMain_all"))


@app.route("/logout")
def logout():
    del login_session["username"]
    del login_session["email"]
    del login_session["image"]
    bookshelves = session.query(Bookshelf).all()
    recent_books = session.query(Book).order_by(desc(Book.id))
    return redirect(url_for("displayMain_all"))


@app.route("/")
@app.route("/bookshelves")
def displayMain_all():

    bookshelves = session.query(Bookshelf).all()
    recent_books = session.query(Book).order_by(desc(Book.id))
    # try an inner join querry:
    creators = getBookshelfCreators()
    return render_template(
        "showAll.html", recentBooks=recent_books,
        bookshelves=bookshelves,
        username=login_session.get("username"),
        image=login_session.get("image"),
        creators=creators)


@app.route("/bookshelves/new", methods=["GET", "POST"])
def newBookshelf():
    if request.method == "GET":
        if "username" in login_session:
            return render_template("newBookshelf.html")
        else:
            return redirect(url_for("loginPage"))
    elif request.method == "POST":
        name = request.form.get("newName")
        image = request.form.get("imageURL")
        user_id = login_session["user_id"]
        if name:
            newBookshelf = Bookshelf(name=name, user_id=user_id)
            if image:
                newBookshelf.image_url = image
            session.add(newBookshelf)
            flash("New bookshelf {} successfully created".format(newBookshelf.name))
            session.commit()
        else:
            flash("Please provide the name of the bookshelf.")
            return redirect(url_for("newBookshelf"))

        return redirect(url_for("displayMain_all"))


@app.route("/bookshelves/<int:bookshelf_id>/")
def bookshelfBooks(bookshelf_id):
    bookshelf = session.query(Bookshelf).get(bookshelf_id)
    books = session.query(Book).filter_by(bookshelf_id=bookshelf_id).all()
    params = {"bookshelf": bookshelf, "books": books}
    return render_template("books.html", **params)


@app.route("/bookshelves/<int:bookshelf_id>/delete", methods=["GET", "POST"])
def deleteBookshelf(bookshelf_id):
    if request.method == "GET":
        if "username" in login_session:
            hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
            if hostBookshelf.user_id != login_session["user_id"]:
                flash("Sorry! Only creators of a particular bookshelf can delete it.")
                return redirect(url_for("displayMain_all"))
            else:
                creators = getBookshelfCreators()
                bookshelf = session.query(Bookshelf).get(bookshelf_id)
                return render_template(
                    "deleteBookshelf.html",
                    bookshelf=bookshelf,
                    creators=creators)
        else:
            return redirect(url_for("loginPage"))
    elif request.method == "POST":
        if request.form.get("delAnswer") == "Yes":
            bookshelfToDelete = session.query(Bookshelf).get(bookshelf_id)
            session.delete(bookshelfToDelete)
            booksToDelete = session.query(Book).filter_by(bookshelf_id=bookshelf_id).all()
            for book in booksToDelete:
                session.delete(book)
            session.commit()
            flash("Bookshelf and all its books have been deleted.")
        return redirect(url_for("displayMain_all"))


@app.route("/bookshelves/<int:bookshelf_id>/edit", methods=["GET", "POST"])
def editBookshelf(bookshelf_id):
    if request.method == "GET":
        if "username" in login_session:
            hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
            if hostBookshelf.user_id != login_session["user_id"]:
                flash("Sorry! Only creators of a particular bookshelf can edit it.")
                return redirect(url_for("displayMain_all"))
            else:
                creators = getBookshelfCreators()
                return render_template(
                    "editBookshelf.html",
                    bookshelf=hostBookshelf,
                    creators=creators)
        else:
            return redirect(url_for("loginPage"))
    elif request.method == "POST":
        bookshelfToBeEdited = session.query(Bookshelf).get(bookshelf_id)
        if request.form["name"]:
            bookshelfToBeEdited.name = request.form["name"]
        if request.form["imageURL"]:
            bookshelfToBeEdited.image_url = request.form["imageURL"]
        session.add(bookshelfToBeEdited)
        session.commit()
        return redirect(url_for("displayMain_all"))


@app.route("/bookshelves/<int:bookshelf_id>/newBook/", methods=["GET", "POST"])
def newBook(bookshelf_id):
    if request.method == "GET":
        if "username" in login_session:
            hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
            if hostBookshelf.user_id != login_session["user_id"]:
                flash("Sorry! Only creators of a particular bookshelf can add \
                edit or delete books.")
                return redirect(
                    url_for(
                        "bookshelfBooks",
                        bookshelf_id=bookshelf_id))
            else:
                return render_template(
                    "newBook.html",
                    bookshelf_id=hostBookshelf.id)
        else:
            return redirect(url_for("loginPage"))
    elif request.method == "POST":
        title = request.form.get("title")
        image = request.form.get("imageURL")
        author = request.form.get("author")
        category = request.form.get("category")
        description = request.form.get("description")
        user_id = login_session["user_id"]
        if title:
            newBook = Book(
                title=title,
                bookshelf_id=bookshelf_id,
                user_id=user_id)
            if image:
                newBook.image_url = image
            if author:
                newBook.author = author
            if category:
                newBook.category = category
            if description:
                newBook.description = description
            session.add(newBook)
            flash("New book {} successfully added.".format(newBook.title))
            session.commit()
        else:
            flash("Please provide the title of the book")
            return redirect(url_for("newBook", bookshelf_id=bookshelf_id))
        return redirect(url_for("bookshelfBooks", bookshelf_id=bookshelf_id))


@app.route("/bookshelves/<int:bookshelf_id>/<int:book_id>/")
def bookItem(bookshelf_id, book_id):
    book = session.query(Book).get(book_id)
    return render_template("bookItem.html", book=book)


@app.route(
    "/bookshelves/<int:bookshelf_id>/<int:book_id>/delete",
    methods=["GET", "POST"])
def deleteBook(bookshelf_id, book_id):
    if request.method == "GET":
        if "username" in login_session:
            hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
            if hostBookshelf.user_id != login_session["user_id"]:
                flash("Sorry! Only creators of a particular bookshelf can add \
                edit or delete books.")
                return redirect(
                    url_for(
                        "bookshelfBooks",
                        bookshelf_id=bookshelf_id))
            else:
                book = session.query(Book).get(book_id)
                return render_template("deleteBook.html", book=book)
        else:
            return redirect(url_for("loginPage"))
    elif request.method == "POST":
        if request.form.get("delAnswer") == "Yes":
            bookToDelete = session.query(Book).get(book_id)
            session.delete(bookToDelete)
            session.commit()
        return redirect(url_for("bookshelfBooks", bookshelf_id=bookshelf_id))


@app.route(
    "/bookshelves/<int:bookshelf_id>/<int:book_id>/edit",
    methods=["GET", "POST"])
def editBook(bookshelf_id, book_id):
    if request.method == "POST":
        hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
        if "username" in login_session:
            if login_session["user_id"] == hostBookshelf.user_id:
                editedBook = session.query(Book).get(book_id)
                if request.form.get("title"):
                    editedBook.title = request.form["title"]
                if request.form.get("author"):
                    editedBook.author = request.form["author"]
                if request.form.get("imageURL"):
                    editedBook.image_url = request.form["imageURL"]
                if request.form.get("catgegory"):
                    editedBook.category = request.form["category"]
                if request.form.get("description"):
                    editedBook.description = request.form["description"]
                session.add(editedBook)
                session.commit()
                return redirect(
                    url_for(
                        "bookshelfBooks",
                        bookshelf_id=bookshelf_id))
            else:
                flash("Sorry! Only creators of a particular bookshelf can add \
                edit or delete books.")
                return redirect(
                    url_for(
                        "books.html",
                        bookshelf_id=bookshelf_id))
        else:
            flash("Please log in in order to edit book items,")
            return redirect("loginPage")

    elif request.method == "GET":
        hostBookshelf = session.query(Bookshelf).get(bookshelf_id)
        if hostBookshelf.user_id != login_session.get("user_id"):
            flash("Sorry! Only creators of a particular book can edit it.")
            return redirect(
                url_for(
                    "bookshelfBooks",
                    bookshelf_id=bookshelf_id))
        else:
            editedBook = session.query(Book).get(book_id)
            return render_template(
                "editBook.html",
                bookshelf=hostBookshelf,
                book=editedBook)


@app.route("/gbooks", methods=["POST"])
def gbooksConnect():
    if request.method == "POST":

        title = request.json["title"]
        author = request.json["author"]
        image = request.json["image"]
        category = request.json["category"]
        description = request.json["description"]
        bookshelf_id = request.json["bookshelf_id"]
        user_id = login_session["user_id"]

        newBook = Book(
            title=title,
            author=author,
            image_url=image,
            category=category,
            description=description,
            user_id=user_id,
            bookshelf_id=bookshelf_id)
        session.add(newBook)
        session.commit()
        return redirect(url_for("bookshelfBooks", bookshelf_id=bookshelf_id))


@app.route("/disconnect")
def disconnect():
    if "provider" in login_session:
        print login_session["provider"]
        if login_session["provider"] == "google":
            gdisconnect()
        if login_session["provider"] == "own":
            logout()
        if login_session["provider"] == "facebook":
            fbdisconnect()
    else:
        del login_session["username"]
        del login_session["email"]
        del login_session["image"]
        print "You are not logged in"
    return redirect(url_for("displayMain_all"))

# User helper functions


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def createUser(login_session):
    newUser = User(
        username=login_session["username"],
        email=login_session["email"],
        user_img=login_session["image"])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session["email"]).one()
    return user.id


def getBookshelfCreators():
    try:
        allCreators = dict(
            session.query(
                Bookshelf.name, User.username).join(
                    User, User.id == Bookshelf.user_id).all())
        return allCreators
    except:
        return None

if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host="0.0.0.0", port=5000)
