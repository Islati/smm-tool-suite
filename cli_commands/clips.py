import click
from tabulate import tabulate

from webapp.models import VideoClip as BotClip

def view_clips():
    clips = BotClip.query.all()
    click.echo(f"Clips Edited: {len(clips)}")

    if len(clips) == 0:
        return

    clip_info = []

    for clip in clips:
        clip_info.append(
            (clip.id, clip.title.strip()[0:30].strip(), clip.start_time, clip.duration, clip.url.strip(),
             clip.upload.access_url.strip() if clip.upload is not None else '-'))

    click.echo(tabulate(clip_info, headers=['ID', 'Video Title', 'Start Time', 'Duration', 'Url',
                                            'Upload (Access) URL']))
