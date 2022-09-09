import click

from bot import VidBot
from bot.webapp.models import VideoClip as BotClip

def redo_clip(clip_id=None, description: str = None, skip_duplicate_check=False, schedule=None, platforms=None,
         title=None):
    clip = BotClip.query.filter_by(id=clip_id).first()

    if clip is None:
        click.echo(f"Could not find clip with id {clip_id}")
        return

    clip_url = clip.url

    if "http" not in clip_url:
        click.echo("Clips need to be recreated from the original video.")
        return

    if "tiktok" not in clip_url and "youtube" not in clip_url:
        click.echo("Requires either a TikTok or YouTube url for the clip")
        return

    tiktok = "tiktok" in clip_url
    youtube = "youtube" in clip_url

    bot = VidBot(youtube_video_download_link=clip.url if youtube else None,
                 tiktok_video_url=clip.url if tiktok else None, clip_length=clip.duration,
                 subclip_start=clip.start_time,
                 output_filename=f"clip_{clip_id}_repost.mp4", post_description=description,
                 skip_duplicate_check=skip_duplicate_check, scheduled_date=schedule,
                 platforms=platforms.split(',') if "," in platforms else [platforms], post_title=title,
                 already_clipped=True)
    bot.chop_and_post_video()
