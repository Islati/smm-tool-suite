import datetime
import json
import math
import mimetypes
import random
import traceback
from pathlib import Path

import maya
import requests
from moviepy.editor import *
from pytube import YouTube
from pytube.cli import on_progress
import click

from tiktok import TikTokDownloader
from webapp.models import VideoClip as BotClip, MediaUpload, SocialMediaPost
from config import DefaultConfig
from ayrshare import SocialPost

api_key = "W8ZMC7Q-PFBMXSB-JPDK8HC-NQPQCXH"
social = SocialPost(api_key)


# todo implement file cleanup.
# todo implement feeds to download images from & repost them


# function to print all the hashtags in a text
def extract_hashtags(text):
    if text is None:
        return []

    # initializing hashtag_list variable
    hashtag_list = []

    # splitting the text into words
    for word in text.split():

        # checking the first character of every word
        if word[0] == '#':
            # adding the word to the hashtag_list
            hashtag_list.append(word[1:])
    return hashtag_list


class VidBot(object):
    """
    Handles the automated process of downloading, chopping, and uploading said video.
    """

    def __init__(self, youtube_video_download_link: str = None, local_video_clip_location: Path = None,
                 tiktok_video_url=None,
                 google_drive_link: str = None, clip_length: int = -1,
                 skip_intro_time: int = 0,
                 output_filename: str = None, post_description: str = None, skip_duplicate_check: bool = False,
                 subclip_start=-1, scheduled_date=None,
                 post_title=None,
                 platforms=["tiktok", "instagram", "twitter", "facebook", "youtube"],
                 application_config=DefaultConfig(), already_clipped=False):
        """
        Initializes the VidBot class with the defined configuration.
        If there's no youtube_video_download_link, then it will use the tiktok_video_url instead.
        If there's no tiktok_video_url, then it will use the local_video_clip_location instead.
        If there's no local_video_clip, then it will use the google_drive_link instead.
        If there's no link available at all it will not initialize.
        :param youtube_video_download_link:
        :param tiktok_video_url: TikTok Video URL
        :param local_video_clip_location:
        :param clip_length:
        :param skip_intro_time:
        :param output_filename:
        :param post_description:
        :param skip_duplicate_check:
        :param subclip_start:
        :param scheduled_date:
        :param platforms:
        """
        self.yt_vid: YouTube = None
        self.youtube_video_download_link = youtube_video_download_link
        self.output_filename = None
        if youtube_video_download_link is not None:
            self.yt_vid: YouTube = YouTube(youtube_video_download_link, on_progress_callback=on_progress)

        self.tiktok_video_url = tiktok_video_url
        self.tiktok_downloader: TikTokDownloader = None
        if self.tiktok_video_url is not None:
            self.tiktok_downloader = TikTokDownloader(self.tiktok_video_url, output_filename=output_filename)
        self.downloaded: bool = False
        # local file
        self.local_video_clip_location = local_video_clip_location
        self.video_path = None if self.local_video_clip_location is None else self.local_video_clip_location
        self.video: VideoFileClip = None if local_video_clip_location is None else VideoFileClip(
            local_video_clip_location)
        self.audio: AudioFileClip = None if self.video is None else self.video.audio
        self.clip_length = clip_length
        # The created subclip
        self.clip: VideoFileClip = None
        # Where the clip is saved
        self.clip_path: Path = None
        self.skip_intro_time = skip_intro_time

        self.output_filename = output_filename
        self.post_description = post_description
        self.skip_duplicate_check = skip_duplicate_check
        self.subclip_start = subclip_start
        self.scheduled_date = scheduled_date
        self.platforms = platforms
        self.post_title = post_title
        if self.post_title is None and self.youtube_video_download_link is not None:
            self.post_title = self.yt_vid.title

        if self.post_title is None and self.tiktok_video_url is not None:
            self.post_title = self.tiktok_downloader.title

        self.application_config = application_config
        self.already_clipped = already_clipped

    def is_local_video(self):
        """
        Check whether or not the video file we're editing is local.
        :return:
        """
        if self.local_video_clip_location is not None:
            return True

        return False

    def check_for_duplicate_clips(self, start_time: int):
        """
        Checks if the video clip already exists in the database by comparing start times.
        :param start_time: start time of the video clip
        :return: True if the clip already exists, False if it does not
        """

        if self.skip_duplicate_check is True:
            return False

        search_clip = BotClip.query.filter_by(start_time=start_time,
                                              url=self.get_video_url()).all()

        if len(search_clip) == 0:
            return False

        for clip in search_clip:
            if clip.upload is not None and clip.upload.uploaded is True:
                return True
        return False

    def download_video(self):
        """
        Downloads the highest possible quality video for creating the clip.
        :return: path of the video downloaded
        """
        if self.youtube_video_download_link is not None:
            path = self.yt_vid.streams.filter(progressive=True).get_highest_resolution().download(
                filename=self.output_filename)
            self.downloaded = True
            self.video_path = path
            self.video = VideoFileClip(path)
            self.audio = self.video.audio
            return path

        if self.tiktok_video_url is not None:
            self.tiktok_downloader.download_video()
            self.downloaded = True
            self.video_path = self.output_filename
            self.video = VideoFileClip(self.output_filename)
            self.audio = self.video.audio
            return self.output_filename

        return None

    def is_downloaded_clip(self):
        """
        Check whether or not the video file we're editing was downloaded by the bot.
        :return:
        """
        if not self.downloaded:
            return False

        if self.youtube_video_download_link is not None:
            return True

        if self.tiktok_video_url is not None:
            return True

        return False

    def get_video_url(self):
        if self.youtube_video_download_link is not None:
            return self.youtube_video_download_link

        if self.tiktok_video_url is not None:
            return self.tiktok_video_url

        return None

    def create_video_clip(self):
        """
        Clips the video to the defined length.
        :param check_duplicates: Check if the clip already exists by comparing start times in the database
        :return: path of the clip
        """

        # Download clip if it's not local
        if not self.is_downloaded_clip() and not self.is_local_video():
            self.download_video()

        # get a random start time
        start_time = self.get_random_start_time() if self.subclip_start == -1 else self.subclip_start
        # CHECK FOR DUPLICATE CLIPS IN DB **
        if self.check_for_duplicate_clips(start_time):
            print(f"Duplicate clip starting @ {start_time}s! Retrying...")
            return self.create_video_clip()
        if self.clip_length == -1:
            self.clip_length = self.video.duration
            # write the entry to the db
            video_clip_record = BotClip(url=self.get_video_url(), title=self.post_title,
                                        start_time=start_time,
                                        duration=self.video.duration)
            video_clip_record.save(commit=True)

            print(
                f"Created database entry ({video_clip_record.id}) for video clip of {self.output_filename} starting @ {start_time}s")
            return f"{self.output_filename}", video_clip_record

        end_time = start_time + self.clip_length
        print(f"Clipping video from {start_time}s to {end_time}s")
        # Create & save the clip

        self.clip = self.video.subclip(start_time, end_time)
        audio_clip = self.video.audio.subclip(start_time, end_time)

        self.clip = self.clip.set_audio(audio_clip)
        self.clip.write_videofile(f"{self.output_filename}",
                                  temp_audiofile=f"{self.output_filename.replace('.', '_')}_tempaudio.m4a",
                                  codec="libx264",
                                  audio_codec="aac", remove_temp=False)
        self.clip.close()
        # invoke ffmpeg to append audio subclip.
        import subprocess as sp
        command = ['ffmpeg',
                   '-y',  # approve output file overwite
                   '-i', f"{self.output_filename}",
                   '-i', f"{self.output_filename.replace('.', '_')}_tempaudio.m4a",
                   '-c:v', 'copy',
                   '-c:a', 'aac',  # to convert mp3 to aac
                   '-shortest',
                   f"{self.output_filename}"]

        print(f"Running command: {' '.join(command)}")
        process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
        process.wait()

        # write the entry to the db
        video_clip_record = BotClip(url=self.get_video_url(), title=self.post_title,
                                    start_time=start_time,
                                    duration=self.clip_length)
        video_clip_record.save(commit=True)

        print(
            f"Created database entry ({video_clip_record.id}) for video clip of {self.post_title} starting @ {start_time}s")
        return f"{self.output_filename}", video_clip_record

    def get_random_start_time(self):
        """
        Generate a random start time for the clip.
        Created using the formula:
        r   andom_start_time = random.randint(0 + skip_intro_time, video_duration - clip_length)
        :return:
        """
        return random.randint(0 + self.skip_intro_time, math.floor(self.video.duration - self.clip_length))

    def upload_file_to_cloud(self, video_clip: VideoClip):
        """
        Uploads the video clip to social media via the API.
        :return:
        """
        # retrieve the information
        req = requests.get("https://app.ayrshare.com/api/media/uploadUrl",
                           headers={'Authorization': f'Bearer {api_key}'},
                           params={'contentType': mimetypes.guess_type(self.output_filename),
                                   'fileName': f"{self.output_filename}"})

        upload_request_response = req.json()

        media_upload = MediaUpload(access_url=upload_request_response['accessUrl'],
                                   content_type=upload_request_response['contentType'],
                                   upload_url=upload_request_response['uploadUrl'], clip=video_clip)
        media_upload.save(commit=True)

        # upload the video

        req = requests.put(upload_request_response['uploadUrl'],
                           headers={'Content-Type': upload_request_response['contentType']},
                           data=open(f"{self.output_filename}", 'rb'))

        if req.status_code == 200:
            return media_upload

        print(f"Upload failed with status code {req.status_code}")
        return None

    def validate_json(self, json_body):
        req = requests.post("https://app.ayrshare.com/validateJSON", headers={"Content-Type": "text/plain"},
                            data=json_body)
        print(req.text)

    def compile_keywords(self):
        """
        Compile the keywords (hashtags) for this vid. Uses the provided description, and any online source if available.
        :return:
        """
        keywords = extract_hashtags(self.post_description)
        keyword_length = 0

        for keyword in keywords:
            keyword_length += len(keyword)
            if keyword_length >= 400:
                break

        if self.youtube_video_download_link is not None:
            for keyword in self.yt_vid.keywords:
                if keyword_length >= 400 or len(keyword) + keyword_length >= 400:
                    break

                keywords.append(keyword)
                keyword_length += len(keyword)

        if self.tiktok_video_url is not None:
            for keyword in self.tiktok_downloader.hashtags:
                if keyword_length >= 400 or len(keyword) + keyword_length >= 400:
                    break

                keywords.append(keyword)
                keyword_length += len(keyword)

        keywords = list(set(keywords))
        return keywords

    def compile_hashtag_string(self):
        _str = ""
        for keyword in self.compile_keywords():
            _str += f"#{keyword} "
        return _str

    def is_image_file(self, file):
        return mimetypes.guess_type(file)[0].startswith('image')

    def is_video_file(self, file):
        """
        Checks if the file is a video file.
        :param file:
        :return:
        """
        mimetype = mimetypes.guess_type(file)[0]
        return "video" in mimetype

    def parse_tags(self, string):
        """
        Parse tags from the configuration file on the given input string, replacing the key with the generated value.
        :param string:
        :return:
        """
        tags = self.application_config.TAGS
        for key, value in tags:
            if key in string:
                if isinstance(value, str):
                    string = string.replace(key, value)
                else:
                    string = string.replace(key, value(self))  # lambda function embed

        return string

    def post_to_socials(self, media_upload: MediaUpload):
        """
        Send the video clip to TikTok via the API.
        Does not currently support setting description / hashtags so these will be done via the user when approving the upload inside the official TikTok API.

        :param media_upload:
        :return:
        """

        date_time = None

        is_video_file = self.is_video_file(self.output_filename)

        platform_defaults = self.application_config.PLATFORM_DEFAULTS

        # post to each social platform one by one,
        for platform in self.platforms:
            post_data = {
                "post": f"{self.post_description}",
                "platforms": platform,
                "mediaUrls": [media_upload.access_url],
                "isVideo": is_video_file,
                "shortenLinks": False,
                "requiresApproval": False,
            }

            # Match the platforms we're
            # with the default values for that platform.
            match platform:
                case "twitter":
                    if 'post' in platform_defaults['twitter'].keys():
                        post_data['post'] = self.parse_tags(platform_defaults['twitter']['post'])[0:280]
                    if self.is_image_file(self.output_filename):
                        post_data['image_alt_text'] = self.parse_tags(platform_defaults['twitter']['image_alt_text'])
                case "instagram":
                    if 'post' in platform_defaults['instagram'].keys():
                        post_data['post'] = self.parse_tags(platform_defaults['instagram']['post'])[0:2200]
                    if self.is_video_file(self.output_filename):
                        post_data["instagramOptions"] = {
                            "reels": True,
                            "shareReelsFeed": True,
                        }
                case "youtube":
                    if 'post' in platform_defaults['youtube'].keys():
                        post_data['post'] = self.parse_tags(platform_defaults['youtube']['post'])

                    post_data["youTubeOptions"] = {
                        "title": self.post_title[0:100],
                        "post": post_data['post'],
                        "tags": self.compile_keywords(),
                        "visibility": platform_defaults['youtube']['visibility'] if 'visibility' in platform_defaults[
                            'youtube'].keys() else "public",
                        "thumbNail": self.yt_vid.thumbnail_url if self.youtube_video_download_link is not None else self.tiktok_downloader.thumbnail_url if self.tiktok_video_url is not None else None,
                        "madeForKids": False,
                        "shorts": True,
                    }

                    if post_data['youTubeOptions']['thumbNail'] is None:
                        del post_data['youTubeOptions']['thumbNail']
                case "facebook":
                    keyword_string = ""
                    for keyword in self.compile_keywords():
                        keyword_string += f"#{keyword} "

                    if 'post' in platform_defaults['facebook'].keys():
                        post_data['post'] = self.parse_tags(platform_defaults['facebook']['post'])
                    post_data['faceBookOptions'] = {
                        "title": self.parse_tags(platform_defaults['facebook']['title']),
                        "altText": self.parse_tags(platform_defaults['facebook']['altText']),
                        "mediaCaptions": self.parse_tags(platform_defaults['facebook']['mediaCaptions']),
                    }

            # If there's a scheduled date set, process that value.
            if self.scheduled_date is not None:
                try:
                    date_time: maya.MayaDT = maya.when(self.scheduled_date, timezone="UTC")
                except:
                    try:
                        date_time: maya.MayaDT = maya.parse(self.scheduled_date, timezone="UTC")
                    except:
                        date_time: maya.MayaDT = maya.MayaDT.from_iso8601(self.scheduled_date)

                post_data['scheduleDate'] = date_time.iso8601()

            # Post the request to AYRShare.
            resp = requests.post("https://app.ayrshare.com/api/post", headers={'Authorization': f'Bearer {api_key}'},
                                 json=post_data)
            if resp.status_code == 200:
                resp = resp.json()
                api_id = resp['id']

                if resp['status'] == 'scheduled':
                    post = SocialMediaPost(api_id=api_id, platform=platform, clip=media_upload.clip,
                                           post_time=date_time.datetime(
                                               to_timezone="UTC") if date_time is not None else datetime.datetime.utcnow()
                                           )
                    post.save(commit=True)
                    print("+ Scheduled on " + platform + " for " + self.scheduled_date)

                elif resp['status'] == 'success':
                    if 'postIds' in resp.keys():
                        for entry in resp['postIds']:
                            if entry['status'] != 'success':
                                print(f"!! Failed to post to {entry['platform']}")
                                continue

                            post = SocialMediaPost(api_id=api_id, platform=entry['platform'],
                                                   post_url=entry['postUrl'] if 'postUrl' in entry.keys() else None,
                                                   clip=media_upload.clip, post_time=date_time.datetime(
                                    to_timezone="UTC") if date_time is not None else datetime.datetime.utcnow())
                            post.save(commit=True)
                            print("+ Posted to " + entry['platform'])

            else:
                print(f"Failed to post to socials with status code {resp.status_code}")
                print(f"Response: {resp.text}")

    def is_slot_ok(self):
        """
        Checks if the slot is ok to post in.
        :return:
        """

        # check if the slot is ok
        if isinstance(self.scheduled_date, maya.MayaDT):
            post_time = self.scheduled_date.datetime(to_timezone="UTC")
        else:
            try:
                post_time = maya.when(self.scheduled_date, timezone="UTC")
            except Exception as e:
                post_time = maya.parse(self.scheduled_date)

        posts_in_slot = SocialMediaPost.query.filter_by(post_time=post_time.datetime()).all()

        if len(posts_in_slot) >= 1:
            return False

    def find_next_slot(self, hours_difference=4, days=1):
        """
        Find the next available slot for the video to be posted.
        :return:
        """

        if self.is_slot_ok():
            return self.scheduled_date

        # check if the slot is ok
        if isinstance(self.scheduled_date, maya.MayaDT):
            post_time = self.scheduled_date.datetime(to_timezone="UTC")
        else:
            try:
                post_time = maya.when(self.scheduled_date, timezone="UTC")
            except Exception as e:
                post_time = maya.parse(self.scheduled_date)

        posts_in_slot = SocialMediaPost.query.filter_by(post_time=post_time.datetime()).all()

        if len(posts_in_slot) >= 1:
            post_time = post_time.add(hours=hours_difference, days=days)
            self.scheduled_date = post_time
            return self.find_next_slot(hours_difference=hours_difference)

        return self.scheduled_date

    def run(self):
        """
        Perform the entire set of operations:
        1. Download the video
        2. Clip the video
        3. Upload the video
        :return:
        """

        if not self.downloaded and (self.youtube_video_download_link is not None or self.tiktok_video_url is not None):
            self.download_video()

        clip_path, clip_record = None, None
        clip_path, clip_record = self.create_video_clip()

        media_file = None
        if clip_record.upload is None:
            upload = click.prompt(f"Upload clip ({self.output_filename}) to social media? [Y/N] ", type=bool)
            if not upload:
                click.echo("Will not using the created clip")
                if click.prompt("Create a new clip? [Y/N] ", type=bool):
                    self.run()
                    return
                else:
                    exit(0)
                return
            media_file = self.upload_file_to_cloud(video_clip=clip_record)
        else:
            media_file = clip_record.upload
            click.echo(f"Reusing existing upload {media_file.access_url}")

        self.post_to_socials(media_file)
        print(
            f"Uploaded clip to {','.join(self.platforms) if ',' in self.platforms else self.platforms} & Recorded this in the database!")

        if "tiktok" in self.platforms:
            print("Open your TiKTok app to describe, hashtag & approve the upload.")


from webapp import create_app
from config import DefaultConfig

config = DefaultConfig()

flask_app = create_app(config)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--yt', '-yt', 'youtube_video_download_link', type=str, default=None)
@click.option('--tiktok', '-tik', 'tiktok_video_link', type=str, required=False, default=None)
@click.option('--local', "local_video_path", type=str, default=None, required=False)
@click.option('--length', '-l', "clip_length", default=-1, help="Length of the clip in seconds")
@click.option('--skip', '-s', "skip_intro_time", default=0, help="Skip the first x seconds of the video")
@click.option('--output', '-o', "output_filename", default=f"{datetime.datetime.utcnow().timestamp()}",
              help="Output path for the video clip", prompt="Filename for your clip")
@click.option("--description", "-d", "description", default=None, help="Description for the post.")
@click.option('--force', '-f', "skip_duplicate_check", is_flag=True, default=False,
              help="Force the post of the video, skipping duplicate cuts.")
@click.option('--schedule', '-t', "schedule", default=None,
              help="Example: tomorrow 10:00 am. If not specified, the video will be posted immediately.")
@click.option('--platforms', '-p', "platforms", default="tiktok,instagram,facebook,twitter,youtube")
@click.option('--title', "title", required=False, help="Provide this if you're giving the clip a new title.")
@click.option('--start', '-st', 'start_time', required=False, default=-1,
              help="Start time of the clip (default random start time)")
def chop(youtube_video_download_link: str = None, tiktok_video_link=None, local_video_path=None, clip_length=33,
         skip_intro_time=0,
         output_filename: str = None,
         description: str = None,
         start_time: int = None,
         skip_duplicate_check=False, schedule=None, platforms=None, title=None):
    """
    Chop a video and post it on social media.
    :param youtube_video_download_link: Youtube video link.
    :param clip_length:
    :param skip_intro_time:
    :param output_filename:
    :param description:
    :param skip_duplicate_check:
    :param schedule:
    :param platforms:
    :return:
    """

    if "." not in output_filename:
        click.echo("Please provide a filename with an extension")
        return

    if youtube_video_download_link is None and local_video_path is None and tiktok_video_link is None:
        click.echo(
            "ERROR: You must provide a video link.\n\n See --help for more information")
        exit(0)
        return

    bot = VidBot(youtube_video_download_link=youtube_video_download_link, tiktok_video_url=tiktok_video_link,
                 local_video_clip_location=local_video_path,
                 clip_length=clip_length,
                 skip_intro_time=skip_intro_time,
                 output_filename=output_filename,
                 subclip_start=start_time,
                 post_description=description, skip_duplicate_check=skip_duplicate_check, scheduled_date=schedule,
                 platforms=platforms.split(',') if "," in platforms else [platforms], post_title=title)
    bot.run()


@cli.command('set_upload_schedule')
def set_upload_schedule():
    resp = social.setAutoSchedule({
        'schedule': ['00:00Z', '12:00Z', '16:20Z', '19:00Z', '21:00Z'],
        'title': 'default',
        'setStartDate': '2022-09-04:00:00Z',
    })
    click.echo(resp)


@cli.command('tiktok_download')
@click.argument('url')
@click.argument("output_filename")
def tiktok_download(url, output_filename):
    if "." not in output_filename:
        click.echo("Please provide a filename with an extension")
        return
    downloader = TikTokDownloader(url, output_filename=output_filename)
    downloader.download_video()
    print(f"Downloaded video to {output_filename}")


@cli.command('clips')
def clips():
    """
    View the clips that have been created.
    :return:
    """
    clips = BotClip.query.all()
    click.echo(f"Clips Edited: {len(clips)}")
    click.echo("---------------")
    click.echo('[ID] | [Date Created] | Video Title | Start Time | Duration | Url | Upload (Access) URL')
    for clip in clips:
        click.echo(
            f"  + {clip.id} | {clip.created_at} | {clip.title} | {clip.start_time}s | {clip.duration}s | {clip.url} | {clip.upload.access_url if clip.upload is not None else 'Not Uploaded'}")
    click.echo("---------------")


@cli.command('redo_clip', help="Post a specific cut of a video to the linked social media accounts")
@click.argument("clip_id")
@click.option('--description', '-d', "description", prompt="Description for the upload.")
@click.option('--force', '-f', "skip_duplicate_check", is_flag=True, default=False,
              help="Force the post of the video, skipping duplicate checks.")
@click.option('--schedule', '-t', "schedule", default=None,
              help="Example: Tomorrow at 4:20 pm. If not specified, the video will be posted immediately.")
@click.option('--platforms', '-p', "platforms", default="tiktok,instagram,facebook,twitter,youtube")
@click.option('--title', "title", required=False, help="Provide this if you're giving the clip a new title.")
def redo_clip(clip_id=None, description: str = None, skip_duplicate_check=False, schedule=None, platforms=None,
              title=None):
    """
    Repost a previously edited clip.
    :param clip_id:
    :param description:
    :param skip_duplicate_check:
    :param schedule:
    :param platforms:
    :param title: Provide this if you're giving the clip a new title.
    :return:
    """
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
    bot.run()


@cli.command('history')
@click.option('--last-days', '-d', "last_days", default=30, help="Number of days to look back.")
@click.option('--last-records', '-r', "last_records", default=100, help="Number of records to look back.")
def history(last_days, last_records):
    """
    View post history from the Ayrshare api (messy)
    :param last_days:
    :param last_records:
    :return:
    """
    req = requests.get('https://app.ayrshare.com/api/history',
                       params={'lastDays': last_days, 'lastRecords': last_records},
                       headers={'Authorization': f'Bearer {api_key}'})

    from pprint import pprint
    pprint(req.json())


@cli.command('post_info')
@click.option('--clip-id', '-c', "clip_id", default=None, help="Post ID to get info for.")
@click.option('--video-url', '-v', "video_url", default=None, help="Video URL to get info for.")
def post_info(clip_id=None, video_url=None, print_intro_header=True):
    """
    View information about a post via its clip id (acquired using the clips command) or video url.
    :param clip_id:
    :param video_url:
    :return:
    """
    if clip_id is None and video_url is None:
        click.echo("Please provide a clip id or video url")
        return

    if "," in clip_id:
        print(f"---- CLIP POST INFORMATION ----")
        print('[PLATFORM] | [TYPE] | [POST ID] | [STATUS] | [CREATED] | [SCHEDULE_DATE] | [POST] | [URL]')
        for clip_id in clip_id.split(","):
            clip = BotClip.query.filter_by(id=clip_id).first()

            posts_with_clip = SocialMediaPost.query.filter_by(clip_id=clip.id).all()
            if posts_with_clip is None or len(posts_with_clip) == 0:
                continue

            for post in posts_with_clip:
                req = requests.get(f'https://app.ayrshare.com/api/history/{post.api_id}',
                                   headers={'Authorization': f'Bearer {api_key}'})
                resp = req.json()
                post_url = post.post_url
                if post_url is None:
                    try:
                        post_url = resp['postIds'][0]['postUrl']
                    except:
                        pass
                print(
                    f"{post.platform} | {resp['type']} | {resp['id']} | {resp['status']} | {resp['created']} | {resp['scheduleDate']['utc'] if 'scheduleDate' in resp.keys() else 'N/A'} | ... | {post_url}")

        print('---------------------------------')

    clip = None

    if video_url is not None:
        clip = BotClip.query.filter_by(url=video_url).first()

    if clip_id is not None:
        clip = BotClip.query.filter_by(id=clip_id).first()

    if clip is None:
        click.echo(f"Could not find clip with id {clip_id} or url {video_url}")
        return

    posts_with_clip = SocialMediaPost.query.filter_by(clip_id=clip.id).all()
    if posts_with_clip is None or len(posts_with_clip) == 0:
        click.echo(f"Could not find any posts with clip id {clip_id}")
        return

    if print_intro_header:
        print(f"---- CLIP POST INFORMATION ----")
        print('[PLATFORM] | [TYPE] | [POST ID] | [STATUS] | [CREATED] | [SCHEDULE_DATE] | [POST] | [URL]')
    ids = []
    for post in posts_with_clip:
        ids.append(post.api_id)

        req = requests.get(f'https://app.ayrshare.com/api/history/{post.api_id}',
                           headers={'Authorization': f'Bearer {api_key}'})
        resp = req.json()
        print(
            f"{post.platform} | {resp['type']} | {resp['id']} | {resp['status']} | {resp['created']} | {resp['scheduleDate']['utc'] if 'scheduleDate' in resp.keys() else 'N/A'} | {resp['post']} | {post.post_url if post.post_url is not None else resp['postIds'][0]['postUrl'] if 'postIds' in resp.keys() else 'N/A'}")

    if print_intro_header:
        print('----------------------------------')


if __name__ == '__main__':
    cli()
