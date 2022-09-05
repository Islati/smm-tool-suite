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


class DefaultConfig(object):
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
        ('[keywords]', lambda vidbot: vidbot.yt_vid.hashtags),
        ('[ytthumbnail]', lambda vidbot: vidbot.yt_vid.thumbnail_url),
        ('[desc]', lambda vidbot: vidbot.post_description),
        ('[reddit-post-title]', lambda vidbot: vidbot.reddit_post.title if vidbot.reddit_post is not None else "")
    ]

    PLATFORM_DEFAULTS = {
        'twitter': {
            'post': '🎶 Music @ http://skreet.ca 🔗 Follow, Like & Retweet \n\n[desc]',
            'image_alt_text': "[title]"
        },
        'instagram': {
            'post': '🎶 Music @ http://skreet.ca 🔗 Follow, Like & Comment\n[desc]',
        },
        'youtube': {
            'post': '🎶 Music @ http://skreet.ca 🔗 Like, Subscribe & Share \n[viddesc]\n[desc]',
            'visibility': "public",
        },
        "facebook": {
            'post': '🎶 Music @ http://skreet.ca 🔗 Like, Share, Follow & Comment \n[viddesc] [desc]',
            'title': '[title]',
            'altText': '[title]',
            'mediaCaptions': '🎶 Music @ http://skreet.ca 🔗 Like, Subscribe & Share [viddesc]\n\n[desc]'
        }
    }
