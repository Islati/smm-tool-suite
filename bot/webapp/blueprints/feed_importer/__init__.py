import mimetypes
from urllib.parse import urlparse
import os

import requests
from flask import Blueprint, render_template, request, jsonify
from praw.reddit import Submission

from bot import VidBot, utils
from bot.services.reddit import client as reddit_client
from bot.webapp.models import RedditRepost, ImageDb

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

    # Get submission from reddit API (PRAW object)
    post = Submission(reddit=reddit_client.reddit, url=media_url)

    content_type = mimetypes.guess_type(media_url)[0]
    extension = mimetypes.guess_extension(content_type)
    output_file_name = os.path.basename(urlparse(media_url).path)  # Get filename from url path
    # output_file_name = f"meme-{post.id}-post{extension}"

    # download image
    downloaded_file = utils.download_image(media_url, output_file_name)
    if downloaded_file is None or not os.path.exists(downloaded_file):
        return jsonify({"error": "Failed to download image"}), 500

    # try to upload without downloading.
    image_record = ImageDb(url=media_url, title=post.title, description=body)
    image_record.save()

    media_upload = utils.upload_file_to_cloud(downloaded_file, image=image_record)

    if media_upload is None:
        return jsonify({"error": "Failed to upload image to cloud"}), 500

    os.remove(downloaded_file) # remove downloaded file

    # post to socials.s
    # return json for UI display.

    bot = VidBot(
        image_url=media_url,
        output_filename=output_file_name,
        post_description=body,
        skip_duplicate_check=False, scheduled_date=time,
        platforms="facebook", post_title=post.title
    )

    bot.post_image()


@feed_importer.route('/load/', methods=['POST'])
def load(subreddit, sort_method):
    try:
        subreddit_string = request.form['subredditString']
    except:
        subreddit_string = subreddit

    posts = reddit_client.get_posts(subreddit, limit=10)

    # Skip non-image posts & images we've posted before.
    _posts = [post for post in posts if
              (post.is_self is False and RedditRepost.has_been_posted(post.id) is False)]  # link only filter.

    return render_template('feed_importer.html', subreddit=subreddit, posts=_posts)
