# -*- coding: utf-8 -*-
import urllib
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

import webapp2
import jinja2

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Handler(webapp2.RequestHandler):
  """Handler class to handle jinja templates.

  We use jinja2 to use a template html and replace the values we want
  inside this template
  """

  def render(self, template, **kw):
    """Main method to call from our get methods later on"""
    self.write(self.render_str(template,**kw))

  def render_str(self, template, **params):
    """This calls our jinja template we specify and returns a
    processed string.
    """
    template = jinja_env.get_template(template)
    return template.render(params)

  def write(self, *a, **kw):
    """This will write our response HTML back to the client"""
    self.response.write(*a, **kw)


DEFAULT_WALL = 'Public'

# We set a parent key on the 'Post' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.

def wall_key(wall_name=DEFAULT_WALL):
    """Constructs a Datastore key for a Wall entity.

    We use wall_name as the key.
    """
    return ndb.Key('Wall', wall_name)

# [START post]
# These are the objects that will represent our Author and our Post. We're using
# Object Oriented Programming to create objects in order to put them in Google's
# Database. These objects inherit Googles ndb.Model class.
class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
    """A main model for representing an individual post entry."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
# [END post]


# [START main_page]
class MainPage(Handler):
    def get(self):
        wall_name = self.request.get('wall_name',DEFAULT_WALL)
        if wall_name == DEFAULT_WALL.lower(): wall_name = DEFAULT_WALL

        posts_to_fetch = 10
        # If we came from a page that had more than 10 posts, we are continuing
        # the page
        cursor_url = self.request.get('continue_posts')

        # Start creating an arguments dictinoary to pass on to our jinja2 templates
        # when we render the page.
        arguments = {'wall_name': wall_name}

        # Ancestor Queries, as shown here, are strongly consistent
        # with the High Replication Datastore. Queries that span
        # entity groups are eventually consistent. If we omitted the
        # ancestor from this query there would be a slight chance that
        # Greeting that had just been written would not show up in a
        # query.
        # [START query]
        posts_query = Post.query(ancestor = wall_key(wall_name)).order(-Post.date)

        # The function fetch_page() takes a query object and returns three things:
        # a list of post objects, a cursor to indicate where I am currently in the
        # database and a boolean to indicate whether there are more posts that I
        # can further get
        posts, cursor, more = posts_query.fetch_page(posts_to_fetch, start_cursor =
            Cursor(urlsafe=cursor_url))
        # [END query]

        # If there are more posts, we'll add a parameter so we can process this
        # parameter in the next GET request
        if more:
            arguments['continue_posts'] = cursor.urlsafe()

        # Add our posts to our argument dictionary to pass on to the jinja2 template.
        # This is how we pass our past posts data into jinja2 to process the HTML.
        arguments['posts'] = posts

        # If a person is logged in to Google's Services
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            user = 'Anonymous Poster'
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        # Create an arguments dictionary to pass onto the jinja2 templates
        arguments['user_name'] = user
        arguments['url'] = url
        arguments['url_linktext'] = url_linktext

        # Write Out Page
        self.render('lesson_one.html')
        self.render('lesson_two.html')
        self.render('lesson_three.html')
        self.render('lesson_four.html')
        self.render('posts.html', **arguments)

# [END main_page]

# [START wall]
class PostWall(webapp2.RequestHandler):
    def post(self):
        # We set the same parent key on the 'Post' to ensure each
        # Post is in the same entity group. Queries across the
        # single entity group will be consistent. However, the write
        # rate to a single entity group should be limited to
        # ~1/second.
        wall_name = self.request.get('wall_name',DEFAULT_WALL)
        post = Post(parent=wall_key(wall_name))

        # When the person is making the post, check to see whether the person
        # is looged into Google
        if users.get_current_user():
            post.author = Author(
                    identity=users.get_current_user().user_id(),
                    name=users.get_current_user().nickname(),
                    email=users.get_current_user().email())

        # Get the content from our request parameters, in this case, the message
        # is in the parameter 'content'
        content = self.request.get('content')

        # Make sure we can convert all types of string that we may get to unicode
        # This helps ensure we can process other other languages besides English
        if type(content) != unicode:
            post.content = unicode(self.request.get('content'),'utf-8')
        else:
            post.content = self.request.get('content')

        # Write to the Google Database
        post.put()

        # Redirect the site
        query_params = {'wall_name': wall_name}
        self.redirect('/?' + urllib.urlencode(query_params))


# [END wall]

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', PostWall),

], debug=True)