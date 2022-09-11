from flask import Blueprint, render_template, request
from bot.services.reddit import client as reddit_client

feed_importer = Blueprint('feed_importer', __name__, template_folder='templates', static_folder='static',
                          url_prefix='/feed-importer')


@feed_importer.route('/', methods=['GET'])
def index():
    return load("rapmemes", "hot")


valid_sort_methods = ('hot', 'new', 'rising', 'controversial', 'top')


@feed_importer.route('/schedule/', methods=['POST'])
def schedule():
    _json = request.get_json(force=True)
    media_url = _json['postUrl']
    body = _json['body']
    time = _json['time']

@feed_importer.route('/load/', methods=['POST'])
def load(subreddit, sort_method):
    try:
        subreddit_string = request.form['subredditString']
    except:
        subreddit_string = subreddit

    posts = reddit_client.get_posts(subreddit, limit=10)

    _posts = [post for post in posts if not post.is_self]  # link only filter.

    return render_template('feed_importer.html', subreddit=subreddit, posts=_posts)
