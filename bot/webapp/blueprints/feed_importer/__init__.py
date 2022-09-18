import mimetypes
from urllib.parse import urlparse
import os

import requests
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from praw.reddit import Submission

from bot.services.reddit import client as reddit_client
from bot.webapp.models import RedditRepost, ImageDb, SocialMediaPost

feed_importer = Blueprint('feed_importer', __name__, template_folder='templates', static_folder='static',
                          url_prefix='/feed-importer')


@feed_importer.route('/', methods=['GET'])
def index():
    return load("rapmemes", "hot")


valid_sort_methods = ('hot', 'new', 'rising', 'controversial', 'top')


@feed_importer.route('/schedule/', methods=['POST'])
def schedule():
    from bot.utils import upload_file_to_cloud, post_to_social, download_image, get_maya_time

    _json = request.form
    post_id = _json['postId']
    media_url = _json['postUrl']
    body = _json['body']
    time = _json['time']
    platforms = _json['platforms']
    tags = _json['tags'] if 'tags' in _json.keys() else []

    # Get submission from reddit API (PRAW object)
    post = Submission(reddit=reddit_client.reddit, id=post_id)

    content_type = mimetypes.guess_type(media_url)[0]
    extension = mimetypes.guess_extension(content_type)
    output_file_name = os.path.basename(urlparse(media_url).path)  # Get filename from url path
    # output_file_name = f"meme-{post.id}-post{extension}"

    # download image
    downloaded_file = download_image(media_url, output_file_name)
    if downloaded_file is None or not os.path.exists(downloaded_file):
        flash("Failed to download image", "error")
        return redirect(url_for('feed_importer.index'))

    # try to upload without downloading.
    image_record = ImageDb(url=media_url, title=post.title, description=body)
    image_record.save()

    media_upload = upload_file_to_cloud(downloaded_file, image=image_record)

    if media_upload is None:
        flash("Failed to upload image", "error")
        return redirect(url_for('feed_importer.index'))

    os.remove(downloaded_file)  # remove downloaded file

    social_media_post = SocialMediaPost(None, platforms=platforms,
                                        post_time=get_maya_time(time).datetime(to_timezone='UTC'),
                                        media_upload=media_upload, hashtags=tags, post_url=media_url, title=post.title,
                                        description=body)

    success, api_key, status_code, response_text = post_to_social(platforms.split(',') if (',' in platforms and isinstance(platforms,str)) else [platforms],
                                                                  social_media_post)  # all that's required for an image post.

    social_media_post.save(commit=True)
    if not success:
        flash(f"Failed to post to social media.\nStatus Code: {status_code}\nResponse: {response_text}", "error")
        return redirect(url_for('feed_importer.index'))
        # post to socials.s
    # return json for UI display.
    flash("Successfully created post!", "success")
    reddit_repost = RedditRepost(post_id=post.id, title=post.title, url=post.url)
    return redirect(url_for('feed_importer.index'))


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
