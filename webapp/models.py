import datetime

import maya
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from webapp.database import db, SqlModel, SurrogatePK, TimeMixin

"""
Secondary table for the social media posts to show many-to-many relationship with hashtags.
"""
post_hashtags_table = db.Table('post_hashtags',
                               db.Column('post_id', db.Integer, db.ForeignKey('social_media_posts.id')),
                               db.Column('hashtag_id', db.Integer, db.ForeignKey('hashtags.id')))


class Hashtag(SurrogatePK, TimeMixin, SqlModel):
    """
    Hashtags used on posts.
    :param SurrogatePK:
    :param TimeMixin:
    :param SqlModel:
    :return:
    """
    __tablename__ = "hashtags"

    name = db.Column(db.String(255), nullable=False)

    def __init__(self, name):
        super().__init__(name=name)


class ImageDb(SurrogatePK, TimeMixin, SqlModel):
    """
    Image class. Used for posts.
    """
    __tablename__ = "images"

    url = db.Column(db.String(255), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)

    def __init__(self, url, title, description):
        super().__init__(url=url, title=title, description=description)


class VideoClip(SurrogatePK, TimeMixin, SqlModel):
    """
    Represents a previously created video clip (with the bot)
    """
    __tablename__ = "video_clips"

    url = db.Column(db.String(255), nullable=False)
    title = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)

    def __init__(self, url, title, start_time, duration):
        super().__init__(url=url, title=title, start_time=start_time, duration=duration)


class MediaUpload(SurrogatePK, TimeMixin, SqlModel):
    """
    Represents a media upload to the API
    """
    __tablename__ = "media_uploads"

    access_url = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Text, nullable=False)
    upload_url = db.Column(db.Text, nullable=False)

    uploaded = db.Column(db.Boolean, default=False)

    clip = db.relationship("VideoClip", backref=backref("upload", uselist=False), uselist=False)
    clip_id = db.Column(db.Integer, db.ForeignKey('video_clips.id'), nullable=True)

    image = db.relationship("ImageDb", backref=backref("upload", uselist=False), uselist=False)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)

    def __init__(self, access_url, content_type, upload_url, clip=None, image=None):
        super().__init__(access_url=access_url, content_type=content_type, upload_url=upload_url, uploaded=False,
                         clip=clip, clip_id=clip.id if clip is not None else None, image=image,
                         image_id=image.id if image is not None else None)

    @hybrid_property
    def is_expired(self):
        return datetime.datetime.utcnow() >= self.created_at + datetime.timedelta(days=30)

    @hybrid_property
    def is_video(self):
        return self.clip is not None

    @hybrid_property
    def is_image(self):
        return self.image is not None


class SocialMediaPost(SurrogatePK, TimeMixin, SqlModel):
    """
    Represents a social media post made with the API
    """
    __tablename__ = "social_media_posts"

    api_id = db.Column(db.Text, nullable=False)
    platform = db.Column(db.Text, nullable=False)
    post_url = db.Column(db.Text, nullable=True)

    post_time = db.Column(db.DateTime, nullable=True)

    media_upload = db.relationship("MediaUpload", backref=backref("social_media_post", uselist=False), uselist=False)
    media_upload_id = db.Column(db.Integer, db.ForeignKey('media_uploads.id'), nullable=True)

    hashtags = db.relationship("Hashtag", secondary=post_hashtags_table, backref="posts")

    def __init__(self, api_id, platform, post_time, media_upload, hashtags, post_url=None):
        super().__init__(api_id=api_id, platform=platform,
                         post_time=maya.MayaDT.from_iso8601(post_time).datetime(),
                         post_url=post_url,
                         media_upload=media_upload,
                         media_upload_id=media_upload.id,
                         hashtags=[Hashtag.get_or_create(name=hashtag) for hashtag in hashtags])
