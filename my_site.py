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
    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


DEFAULT_PAGE = 'Logans Page'

def wall_key(mypage_name=DEFAULT_PAGE):
    return ndb.Key('Wall', mypage_name)

class Author(ndb.Model):
    identity = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(Handler):
    def get(self):
        mypage_name = self.request.get('mypage_name',DEFAULT_PAGE)
        if mypage_name == DEFAULT_PAGE.lower(): mypage_name = DEFAULT_PAGE

        posts_to_fetch = 10
        cursor_url = self.request.get('continue_posts')
        arguments = {'mypage_name': mypage_name}
        posts_query = Post.query(ancestor = wall_key(mypage_name)).order(-Post.date)
        posts, cursor, more = posts_query.fetch_page(posts_to_fetch, start_cursor =
            Cursor(urlsafe=cursor_url))

        if more:
            arguments['continue_posts'] = cursor.urlsafe()
        arguments['posts'] = posts
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            user = 'Anonymous Poster'
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        arguments['user_name'] = user
        arguments['url'] = url
        arguments['url_linktext'] = url_linktext


        self.render('notes.html', **arguments)

class PostWall(webapp2.RequestHandler):
    def post(self):
        mypage_name = self.request.get('mypage_name',DEFAULT_PAGE)
        post = Post(parent=wall_key(mypage_name))

        if users.get_current_user():
            post.author = Author(
                    identity=users.get_current_user().user_id(),
                    name=users.get_current_user().nickname(),
                    email=users.get_current_user().email())

        content = self.request.get('content')

        if type(content) != unicode:
            post.content = unicode(self.request.get('content'),'utf-8')
        else:
            post.content = self.request.get('content')
        post.put()

        query_params = {'mypage_name': mypage_name}
        self.redirect('/?' + urllib.urlencode(query_params))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', PostWall),

], debug=True)