import datetime

import maya
from sqlalchemy.orm import backref

from webapp.database import db, SqlModel, SurrogatePK, TimeMixin


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
    clip_id = db.Column(db.Integer, db.ForeignKey('video_clips.id'), nullable=False)

    def __init__(self, access_url, content_type, upload_url, clip):
        super().__init__(access_url=access_url, content_type=content_type, upload_url=upload_url, uploaded=False,
                         clip=clip, clip_id=clip.id)

    def is_expired(self):
        return datetime.datetime.utcnow() >= self.created_at + datetime.timedelta(days=30)


class SocialMediaPost(SurrogatePK, TimeMixin, SqlModel):
    """
    Represents a social media post made with the API
    """
    __tablename__ = "social_media_posts"

    api_id = db.Column(db.Text, nullable=False)
    platform = db.Column(db.Text, nullable=False)
    post_url = db.Column(db.Text, nullable=True)

    post_time = db.Column(db.DateTime, nullable=True)

    clip = db.relationship("VideoClip", backref=backref("posts", uselist=True), uselist=False)
    clip_id = db.Column(db.Integer, db.ForeignKey('video_clips.id'), nullable=True)

    def __init__(self, api_id, platform, post_time, post_url=None, clip=None):
        super().__init__(api_id=api_id, platform=platform,
                         post_time=maya.MayaDT.from_iso8601(post_time).datetime(),
                         post_url=post_url, clip=clip,
                         clip_id=clip.id if clip else None)
