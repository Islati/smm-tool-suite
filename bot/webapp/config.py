class Config(object):
    """
    Base configuration object.
    """
    Debug = True,
    SQLALCHEMY_DATABASE_URI = "postgresql://islatisk@localhost:5432/vidbot"
    POSTS = []

    TAGS = [
        ('[ytdesc]', lambda vidbot: vidbot.yt_vid.description),
        ('[yttitle]', lambda vidbot: vidbot.yt_vid.title),
    ]

    MAIL_SERVER = 'smtp.mailtrap.io'
    MAIL_PORT = 2525
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEBUG = True
    MAIL_USERNAME = "d9dc9342b9dd8c"
    MAIL_PASSWORD = "7f510c33d434f1"
    MAIL_DEFAULT_SENDER = None
    MAIL_MAX_EMAILS = None
    MAIL_SUPPRESS_SEND = False
    MAIL_ASCII_ATTACHMENTS = False

    API_KEY = "W8ZMC7Q-PFBMXSB-JPDK8HC-NQPQCXH"


class DefaultConfig(Config):
    """
    Configure the applications values & behaviour.
    """

    Debug = True
    SQLALCHEMY_DATABASE_URI = "postgresql://islatisk@localhost:5432/vidbot"

    TAGS = [
        ('[bio]', '🎶 Music Link in Bio 🔗'),
        ('[ytchannel]', 'https://www.youtube.com/channel/UC1HBD9-ZHbEe1cN8Pa2BL_g'),
        ('[ytvid]', lambda vidbot: vidbot.yt_vid.url),
        ('[skreet]', 'skreet.ca'),
        ('[viddesc]',
         lambda
             vidbot: vidbot.yt_vid.description if vidbot.youtube_video_download_link is not None else vidbot.tiktok_downloader.title if vidbot.tiktok_downloader is not None else ""),
        ('[title]',
         lambda vidbot: vidbot.yt_vid.title if vidbot.youtube_video_download_link is not None else vidbot.post_title),
        ('[keywords]', lambda vidbot: vidbot.compile_keywords()),
        ('[hashtags]', lambda vidbot: vidbot.compile_hashtag_string()),
        ('[ytthumbnail]', lambda vidbot: vidbot.yt_vid.thumbnail_url),
        ('[desc]', lambda vidbot: vidbot.post_description),
        ('[reddit-post-title]', lambda vidbot: vidbot.reddit_post.title if vidbot.reddit_post is not None else "")
    ]

    PLATFORM_DEFAULTS = {
        'twitter': {
            'post': '🎶 Music @ http://skreet.ca 🔗 Follow, Like & Retweet \n\n[desc] [hashtags]',
            'image_alt_text': "[title]"
        },
        'instagram': {
            'post': '🎶 Music @ http://skreet.ca 🔗 Follow, Like & Comment\n[desc] [hashtags]',
        },
        'youtube': {
            'post': '[desc] 🎶 Music @ http://skreet.ca 🔗 Like, Subscribe & Share \n[viddesc]',
            'visibility': "public",
        },
        "facebook": {
            'post': '[desc] \n 🎶 Music @ http://skreet.ca 🔗 Like, Share, Follow & Comment \n[viddesc] [hashtags]',
            'title': '[title]',
            'altText': '[desc]',
            'mediaCaptions': '[desc] \n 🎶 Music @ http://skreet.ca 🔗 Like, Share, Follow & Comment \n[viddesc] [hashtags]'
        }
    }
