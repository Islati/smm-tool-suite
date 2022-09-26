import mimetypes
import pprint
import traceback
from urllib.parse import urlparse
import os

import requests
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, make_response
from flask_cors import cross_origin
from praw.reddit import Submission

from bot import utils
from bot.services.reddit import client as reddit_client
from bot.webapp.models import RedditRepost, ImageDb, SocialMediaPost

feed_importer = Blueprint('feed_importer', __name__, template_folder='templates', static_folder='static',
                          url_prefix='/feed-importer')


# todo implement saved subreddits for reposts.

def _get_posts(subreddit, sort_method, limit, allow_reposts=True):
    posts = reddit_client.get_posts(subreddit, limit=limit, sort_method=sort_method)

    # Skip non-image posts & images we've posted before.
    _posts = []
    for post in posts:
        if post.is_self:
            continue

        repost = False

        if RedditRepost.has_been_posted(post.id):
            if not allow_reposts:
                continue

            repost = True

        if post.url is None:
            continue

        if not utils.is_image_file(post.url):
            continue

        _posts.append(
            dict(
                id=post.id,
                url=post.url,
                permalink=post.permalink,
                thumbnail=post.thumbnail,
                title=post.title,
                score=post.score,
                created_utc=post.created_utc,
                author=post.author.name if post.author else "",
                repost=repost,

            )
        )

    return _posts


@feed_importer.route('/<subreddit>/<sort_method>', methods=['GET'])
@feed_importer.route('/')
def index(subreddit="rap", sort_method="hot"):
    limit = request.args.get('limit', 100)
    reposts = request.args.get('reposts', 'true')
    session['subreddit'] = subreddit
    session['sort_method'] = sort_method
    return render_template("feed_importer.html",
                           posts=_get_posts(subreddit, sort_method=sort_method, limit=limit,
                                            allow_reposts=True if reposts == 'true' else False),
                           subreddit=subreddit, sort_method=sort_method, limit=limit)


valid_sort_methods = ('hot', 'new', 'rising', 'controversial', 'top')


@feed_importer.route('/schedule/', methods=['POST'])
def schedule():
    from bot.utils import upload_file_to_cloud, post_to_social, download_image, get_maya_time

    try:
        _json = request.form
    except:
        _json = request.get_json(force=True)


    post_id = _json['postId']
    media_url = _json['postUrl']
    body = _json['body']
    time = _json['time']
    platforms = _json['platforms']
    tags = _json['tags'] if 'tags' in _json.keys() else []

    subreddit = session.get('subreddit', 'rap')
    sort_method = session.get('sort_method', 'hot')

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
        return redirect(url_for('feed_importer.index', subreddit=subreddit, sort_method=sort_method))

    # try to upload without downloading.
    image_record = ImageDb(url=media_url, title=post.title, description=body)
    image_record.save()

    media_upload = upload_file_to_cloud(downloaded_file, image=image_record)

    if media_upload is None:
        flash("Failed to upload image", "error")
        return redirect(url_for('feed_importer.index', subreddit=subreddit, sort_method=sort_method))

    os.remove(downloaded_file)  # remove downloaded file

    social_media_post = SocialMediaPost(None, platforms=platforms,
                                        post_time=get_maya_time(time).datetime(to_timezone='UTC'),
                                        media_upload=media_upload, hashtags=tags, title=post.title,
                                        description=body)

    success, api_key, status_code, response_text = post_to_social(
        platforms.split(',') if (',' in platforms and isinstance(platforms, str)) else [platforms],
        social_media_post)  # all that's required for an image post.

    social_media_post.save(commit=True)
    if not success:
        flash(f"Failed to post to social media.\nStatus Code: {status_code}\nResponse: {response_text}",
              category="error")
        return redirect(url_for('feed_importer.index', subreddit=subreddit, sort_method=sort_method))
        # post to socials.s
    # return json for UI display.
    flash("Successfully created post!", "success")
    reddit_repost = RedditRepost.query.filter_by(post_id=post.id).first()
    if reddit_repost is None:
        reddit_repost = RedditRepost(post_id=post.id, title=post.title, url=post.url)
    reddit_repost.save(commit=True)
    return redirect(url_for('feed_importer.index', subreddit=subreddit, sort_method=sort_method))
#
# @feed_importer.after_request
# def handle_after_request(f):
#     f.headers['Access-Control-Allow-Origin'] = '*'
#     f.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
#     f.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#     print("Updated Headers")
#     return f

@feed_importer.route('/load/', methods=['POST','OPTIONS'])
def load(subreddit=None, sort_method=None, limit=100):

    if request.method == "OPTIONS":
        return build_cors_preflight_response()
    try:
        _json = request.get_json(force=True)
        subreddit_string = _json['subreddit']
        sort_method_selected = _json['sortType']
        limit = _json['limit']
    except:
        subreddit_string = request.form.get('subreddit', subreddit)
        sort_method_selected = request.form.get('sortMethod', sort_method)
        limit = request.form.get('limit', limit)

    response = jsonify({'posts': _get_posts(subreddit_string, sort_method=sort_method_selected, limit=limit)})

    return utils.add_headers(response)
def build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response