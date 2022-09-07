import datetime
import math
import mimetypes
import random
import shutil
from pathlib import Path

import maya
import requests
from moviepy.config import get_setting
from moviepy.editor import *
from moviepy.tools import subprocess_call
from pytube import YouTube
from pytube.cli import on_progress
import click
from tabulate import tabulate

from tiktok import TikTokDownloader
from webapp.models import VideoClip as BotClip, MediaUpload, SocialMediaPost, ImageDb
from webapp.config import DefaultConfig
from ayrshare import SocialPost

import gdown

api_key = "W8ZMC7Q-PFBMXSB-JPDK8HC-NQPQCXH"
social = SocialPost(api_key)


# todo implement file cleanup.
# todo implement feeds to download images from & repost them
# implement instagram reel download & repost to platforms.


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


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    """ Makes a new video file playing video file ``filename`` between
        the times ``t1`` and ``t2``. """
    name, ext = os.path.splitext(filename)
    if not targetname:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    cmd = [get_setting("FFMPEG_BINARY"), "-y",
           "-i", filename,
           "-ss", "%0.2f" % t1,
           "-t", "%0.2f" % (t2 - t1),
           "-map", "0", "-vcodec", "copy", "-acodec", "copy", targetname]

    subprocess_call(cmd)


class VidBot(object):
    """
    Handles the automated process of downloading, chopping, and uploading said video.
    """

    def __init__(self, youtube_video_download_link: str = None, local_video_clip_location: Path = None,
                 tiktok_video_url=None,
                 image_url=None,
                 local_image_location: Path = None,
                 google_drive_link: str = None, clip_length: int = -1,
                 skip_intro_time: int = 0,
                 output_filename: str = None, post_description: str = None, skip_duplicate_check: bool = False,
                 subclip_start=-1, scheduled_date=None,
                 post_title=None,
                 platforms=["tiktok", "instagram", "twitter", "facebook", "youtube"],
                 application_config=DefaultConfig(), already_clipped=False, ffmpeg=False):
        """
        Initializes the VidBot class with the defined configuration.
        :param youtube_video_download_link: Youtube video download link
        :param tiktok_video_url: TikTok Video URL
        :param image_url: Image URL (Used only for reposting images)
        :param local_video_clip_location: local video file to open for chopping
        :param google_drive_link: Google Drive link to download the video from
        :param clip_length: length of clip to create
        :param skip_intro_time: skip the first x seconds of the video
        :param output_filename: output filename of the video
        :param post_description: description of the post
        :param skip_duplicate_check: skip the duplicate check
        :param subclip_start: start time of the subclip (in seconds). This forces start at the clip
        :param scheduled_date: date to upload the content
        :param platforms: platforms to upload the content to.
        """
        self.yt_vid: YouTube = None
        self.youtube_video_download_link = youtube_video_download_link
        self.output_filename = None
        if youtube_video_download_link is not None:
            self.yt_vid: YouTube = YouTube(youtube_video_download_link, on_progress_callback=on_progress)

        self.image_url = image_url
        self.local_image_location = local_image_location
        self.tiktok_video_url = tiktok_video_url
        self.tiktok_downloader: TikTokDownloader = None
        if self.tiktok_video_url is not None:
            self.tiktok_downloader = TikTokDownloader(self.tiktok_video_url, output_filename=output_filename)

        self.google_drive_link = google_drive_link
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
        self.ffmpeg = ffmpeg  # Whether or not to use ffmpeg to extract the subclip
        self.created_files = [
            "tempaudio.m4a"
        ]  # This will be removed after upload & such :)

    def is_local_video(self):
        """
        Check whether or not the video file we're editing is local.
        :return:
        """
        if self.local_video_clip_location is not None:
            return True

        return False

    def check_for_duplicate_images(self, image_url, local_url):
        """
        Check whether or not the image is a duplicate.
        :param image_url: Image URL
        :param local_url: Local URL
        :return:
        """
        if image_url is not None:
            image = ImageDb.query.filter_by(url=image_url).first()

            if image is not None:
                return True

        if local_url is not None:
            image = ImageDb.query.filter_by(local_url=local_url).first()

            if image is not None:
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

    def download_image(self):
        """
        Downloads the image from the URL
        :return:
        """
        r = requests.get(self.image_url, stream=True)
        if r.status_code == 200:
            with open(self.output_filename, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                return self.output_filename

        return None

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

        if self.google_drive_link is not None:
            gdown.download(self.google_drive_link, self.output_filename, quiet=False)
            if self.is_video_file(self.output_filename):
                self.video_path = self.output_filename
                self.video = VideoFileClip(self.output_filename)
                self.audio = self.video.audio
            else:
                print(f"~ Downloaded {self.output_filename} is not a video file.")
            return self.output_filename

        return None

    def is_downloaded_clip(self):
        """
        Check whether or not the video file we're editing was downloaded by the bot.
        :return:
        """
        if not self.downloaded:
            return False

        if self.google_drive_link is not None:
            return True

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

        if self.google_drive_link is not None:
            return self.google_drive_link

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

        if self.ffmpeg:
            ffmpeg_extract_subclip(self.output_filename, start_time, end_time, targetname=f"sub_{self.output_filename}")
            self.output_filename = f"sub_{self.output_filename}"
            print("New filename: ", self.output_filename)
            self.created_files.append(f"sub_{self.output_filename}")
            # write the entry to the db
        else:
            self.clip = self.video.subclip(start_time, end_time)
            audio_clip = self.video.audio.subclip(start_time, end_time)
            #
            # self.clip = self.clip.set_audio(audio_clip)
            self.clip.write_videofile(f"clip_{self.output_filename}",
                                      temp_audiofile=f"tempaudio.m4a",
                                      audio_codec="aac", remove_temp=False, codec="libx264")
            # self.created_files.append(f"{self.output_filename.replace('.', '_')}_tempaudio.m4a")
            self.created_files.append(f"{self.output_filename}")
            self.created_files.append(f"clip_{self.output_filename}")
            self.clip.close()
            # invoke ffmpeg to append audio subclip.
            import subprocess as sp
            command = ['ffmpeg',
                       '-y',  # approve output file overwite
                       '-i', f"{self.output_filename}",
                       '-i', f"tempaudio.m4a",
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

    def upload_file_to_cloud(self, video_clip: VideoClip = None, image_file=None):
        """
        Uploads the video clip to social media via the API.
        :return:
        """
        assert video_clip is not None or image_file is not None, "No video clip or image file provided to upload."

        # retrieve the information
        req = requests.get("https://app.ayrshare.com/api/media/uploadUrl",
                           headers={'Authorization': f'Bearer {api_key}'},
                           params={'contentType': mimetypes.guess_type(self.output_filename)[0],
                                   'fileName': f"{self.output_filename}"})

        upload_request_response = req.json()

        if image_file is not None:
            media_upload = MediaUpload(access_url=upload_request_response['accessUrl'],
                                       content_type=upload_request_response['contentType'],
                                       upload_url=upload_request_response['uploadUrl'], image=image_file)
        else:
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

                keywords.append(keyword.replace("#", ""))
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
        return _str.replace('##', "#")

    def is_image_file(self, file):
        return 'image' in mimetypes.guess_type(file)[0]

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

        compiled_keyword_list = self.compile_keywords()

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
                    post_data['post'] = post_data['post'][0:280]
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
                        "tags": compiled_keyword_list,
                        "visibility": platform_defaults['youtube']['visibility'] if 'visibility' in platform_defaults[
                            'youtube'].keys() else "public",
                        # todo IMPLEMENT THUMBNAIL CUSTOMIZATION
                        "thumbNail": self.yt_vid.thumbnail_url if self.youtube_video_download_link is not None else self.tiktok_downloader.thumbnail_url if self.tiktok_video_url is not None else None,
                        "madeForKids": False,
                        "shorts": True,
                    }

                    if post_data['youTubeOptions']['thumbNail'] is None:
                        del post_data['youTubeOptions']['thumbNail']
                case "facebook":
                    if 'post' in platform_defaults['facebook'].keys():
                        post_data['post'] = self.parse_tags(platform_defaults['facebook']['post'])

                    post_data['faceBookOptions'] = {
                        "altText": self.parse_tags(platform_defaults['facebook']['altText']),
                        "mediaCaptions": self.parse_tags(platform_defaults['facebook']['mediaCaptions']),
                    }

                    if self.is_video_file(self.output_filename):
                        post_data['faceBookOptions']["title"] = self.parse_tags(platform_defaults['facebook']['title']),

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

            if platform == "twitter":
                post_data['post'] = post_data['post'][0:260]
                print('post data trimmed to  {}'.format(len(post_data['post'])))
            # Post the request to AYRShare.
            resp = requests.post("https://app.ayrshare.com/api/post", headers={'Authorization': f'Bearer {api_key}'},
                                 json=post_data)
            if resp.status_code == 200:
                resp = resp.json()
                api_id = resp['id']

                if resp['status'] == 'scheduled':
                    post = SocialMediaPost(api_id=api_id, platform=platform, media_upload=media_upload,
                                           post_time=date_time.datetime(
                                               to_timezone="UTC") if date_time is not None else datetime.datetime.utcnow(),
                                           hashtags=self.compile_keywords())
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
                                                   media_upload=media_upload, post_time=date_time.datetime(
                                    to_timezone="UTC") if date_time is not None else datetime.datetime.utcnow(),
                                                   hashtags=compiled_keyword_list)
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

    def post_image(self):
        """
        Create a social media post with the image.
        :return:
        """

        if not self.downloaded and self.local_image_location is None:
            print(f"Downloading Image from {self.image_url}")
            self.download_image()

            if not os.path.exists(self.output_filename):
                print(f"Failed downloading {self.image_url} to {self.output_filename}")
                return

            print(f"Downloaded Image to {self.output_filename}")
            self.downloaded = True

        if not self.skip_duplicate_check:
            duplicate = self.check_for_duplicate_images(self.image_url,self.local_image_location)

            if duplicate:
                print(f"Duplicate image found, skipping post.")
                return

        media_upload = self.upload_file_to_cloud(
            image_file=self.local_image_location if self.local_image_location is not None else self.output_filename)

        if click.prompt("Proceed with posting socials?", type=bool, default=True):
            self.post_to_socials(media_upload=media_upload)
            print(
                f"Uploaded image to {','.join(self.platforms) if ',' in self.platforms else self.platforms}")

        if self.local_image_location is not None:
            if click.prompt("Delete local image?", type=bool, default=False):
                os.remove(self.local_image_location)

        if self.output_filename is not None:
            os.remove(self.output_filename)
        print("~ Exiting...")
        return

    def chop_and_post_video(self):
        """
        Perform the entire set of operations:
        1. Download the video
        2. Clip the video
        3. Upload the video
        :return:
        """

        if not self.downloaded and (
                self.google_drive_link is not None or self.youtube_video_download_link is not None or self.tiktok_video_url is not None):
            self.download_video()

        clip_path, clip_record = None, None
        clip_path, clip_record = self.create_video_clip()

        media_file = None
        if clip_record.upload is None:
            upload = click.prompt(
                f"Please preview clip before answering!\nUpload clip ({self.output_filename}) to social media? [Y/N] ",
                type=bool)
            if not upload:
                click.echo("Will not using the created clip")
                if click.prompt("Create a new clip? [Y/N] ", type=bool):
                    self.chop_and_post_video()
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
            f"Uploaded {'clip' if self.is_image_file(self.output_filename) is False else 'image'} to {','.join(self.platforms) if ',' in self.platforms else self.platforms} & Recorded this in the database!")

        if "tiktok" in self.platforms:
            print("Open your TiKTok app to describe, hashtag & approve the upload.")

        if len(self.created_files) > 0:
            click.echo("Cleaning up files...")
            for file in self.created_files:
                os.remove(file)
                print(f"Removed {file}")

        print("Enjoy!")


from webapp import create_app
from webapp.config import DefaultConfig

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
@click.option('--fmpeg', '-fm', 'ffmpeg', required=False, default=False, help="Use ffmpeg to cut the video",
              is_flag=True)
def chop(youtube_video_download_link: str = None, tiktok_video_link=None, local_video_path=None, clip_length=33,
         skip_intro_time=0,
         output_filename: str = None,
         description: str = None,
         start_time: int = None,
         skip_duplicate_check=False, schedule=None, platforms=None, title=None, ffmpeg=False):
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
                 local_video_clip_location=os.path.expanduser(local_video_path),
                 clip_length=clip_length,
                 skip_intro_time=skip_intro_time,
                 output_filename=output_filename,
                 subclip_start=start_time,
                 post_description=description, skip_duplicate_check=skip_duplicate_check, scheduled_date=schedule,
                 platforms=platforms.split(',') if "," in platforms else [platforms], post_title=title, ffmpeg=ffmpeg)
    bot.chop_and_post_video()


@cli.command()
@click.option('--image', '-i', 'image_link', type=str, required=False, default=None, help="Image link")
@click.option('--local', "local_image_file", type=str, default=None, required=False, help="Local image path")
@click.option('--output', '-o', "output_file_name", default=None,
              help="Output path for the video clip")
@click.option("--description", "-d", "description", default=None, help="Description for the post.")
@click.option('--force', '-f', "skip_duplicate_check", is_flag=True, default=False,
              help="Force the post of the video, skipping duplicate cuts.")
@click.option('--schedule', '-t', "schedule", default=None,
              help="Example: tomorrow 10:00 am. If not specified, the video will be posted immediately.")
@click.option('--platforms', '-p', "platforms", default="instagram,facebook,twitter")
@click.option('--title', "title", required=False, help="Provide this if you're giving the clip a new title.")
def image(image_link, local_image_file, output_file_name, post_description, skip_duplicate_check, scheduled_date,
          platforms, post_title):
    """
    Crate an image post on social media.
    :param image_link: link to the image (online)
    :param local_image_file: local image location
    :param output_file_name: output file name (for downloaded file)
    :param post_description: post body.
    :param skip_duplicate_check:
    :param scheduled_date:
    :param platforms:
    :param post_title:
    :return:
    """
    if 'youtube' in platforms or 'tiktok' in platforms:
        click.echo("You can't post an image to Youtube or TikTok")
        return

    bot = VidBot(
        image_url=image_link, local_image_location=os.path.expanduser(local_image_file),
        output_filename=output_file_name,
        post_description=post_description,
        skip_duplicate_check=skip_duplicate_check, scheduled_date=scheduled_date,
        platforms=platforms.split(',') if "," in platforms else [platforms], post_title=post_title
    )

    bot.post_image()


@cli.command('set_upload_schedule')
def set_upload_schedule():
    """
    Set the upload 'auto-post' schedule. Requires modification of the code to change.
    :return:
    """
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
    """
    Download a video from TikTok (Without watermark)
    :param url: tiktok video url
    :param output_filename: local file output
    """
    if "." not in output_filename:
        click.echo("Please provide a filename with an extension")
        return
    downloader = TikTokDownloader(url, output_filename=output_filename)
    downloader.download_video()
    print(f"Downloaded video to {output_filename}")


@cli.command('images')
def images():
    images_uploaded = ImageDb.query.all()
    click.echo(f"Images: {len(images_uploaded)}")

    if len(images_uploaded) == 0:
        return

    image_info = []
    for _img in images_uploaded:
        image_info.append((_img.id, _img.created_at, _img.title, _img.description, _img.url,
                           _img.upload.access_url if _img.upload is not None else '-'))

    click.echo(tabulate(image_info, headers=["ID", "Created At", "Title", "Description", "URL", "Upload URL"]))


@cli.command('clips')
def clips():
    """
    View the clips that have been created.
    :return:
    """
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
    bot.chop_and_post_video()


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
@click.option('--image-id', '-i', 'image_id', default=None, help="Image ID to get post info for.")
@click.option('--url', '-u', "url", default=None, help="URL of media (vid / image) object to get post info for.")
def post_info(clip_id=None, url=None, image_id=None, print_intro_header=True):
    """
    View information about a post via its clip id (acquired using the clips command) or video url.
    :param clip_id:
    :param video_url:
    :return:
    """
    if clip_id is None and url is None and image_id is None:
        click.echo("Please provide a clip id, image_id, or  url")
        return

    # What will be printed to the console (as output) without header / footer details.
    post_info = []
    # ids that will be used to get post info from the api
    post_ids = []

    def get_post_data(post, response):
        """
        Local method to get formatted post information to print, using response (api) and post (database)
        :param post:
        :param response:
        :return:
        """
        post_url = post.post_url
        if post_url is None:
            try:
                post_url = response['postIds'][0]['postUrl']
            except:
                pass

        return (post.platform, response['type'], response['id'], response['status'], response['created'],
                response['scheduleDate']['utc'] if 'scheduleDate' in response.keys() else 'N/A',
                ",".join([hashtag.name for hashtag in post.hashtags]), post_url)

    matching_object = []

    # Handle video clips.
    if (clip_id is not None and "," in clip_id) or (image_id is not None and "," in image_id):

        # Process video clip
        if clip_id is not None:
            for clip_id in clip_id.split(","):
                clip = BotClip.query.filter_by(id=clip_id).first()

                if clip is None:
                    click.echo(f"! Could not find clip with id {clip_id}")
                    continue

                if clip.upload is None:
                    click.echo(f"~ Clip {clip_id} was never uploaded")
                    continue

                matching_object.append(clip.upload)

        if image_id is not None:
            for image_id in image_id.split(","):
                db_image = ImageDb.query.filter_by(id=image_id).first()

                if db_image is None:
                    click.echo(f"! Could not find image with id {image_id}")
                    continue

                if db_image.upload is None:
                    click.echo(f"~ Image {image_id} was never uploaded")
                    continue

                matching_object.append(db_image.upload)

    if clip_id is not None and ',' not in clip_id:
        clip = BotClip.query.filter_by(id=clip_id).first()
        if clip is None:
            click.echo(f"Could not find clip with url {url}")
            return

        if clip.upload is None:
            click.echo(f"~ Clip {clip_id} was never uploaded")
            return

        matching_object.append(clip.upload)

    if image_id is not None and ',' not in image_id:
        db_image = ImageDb.query.filter_by(id=image_id).first()

        if db_image is None:
            click.echo(f"Could not find image with id {image_id}")
            return

        if db_image.upload is None:
            click.echo(f"~ Image {image_id} was never uploaded")
            return

        matching_object.append(db_image.upload)

    if url is not None:
        if 'tiktok' in url or 'youtube' in url or 'drive.google' in url or "youtu.be" in url:
            clip = BotClip.query.filter_by(url=url).first()

            if clip is None:
                click.echo(f"Could not find clip with url {url}")
                return

            if clip.upload is None:
                click.echo(f"~ Clip {clip_id} was never uploaded")
                return

            matching_object.append(clip.upload)
        else:
            db_image = ImageDb.query.filter_by(url=url).first()

            if db_image is None:
                click.echo(f"Could not find image with url {url}")
                return

            if db_image.upload is None:
                click.echo(f"~ Image {image_id} was never uploaded")
                return

            matching_object.append(db_image.upload)

    for upload in matching_object:
        posts_with_clip = SocialMediaPost.query.filter_by(media_upload_id=upload.id).all()
        if posts_with_clip is None:
            click.echo(f"~ Object attached (MediaUpload id({upload.id}) was never posted to social media")
            continue

        for post in posts_with_clip:
            post_ids.append(post.api_id)

    if len(post_ids) == 0:
        click.echo("No posts found")
        return

    for post_id in post_ids:
        # Get post info from the api
        posts_with_clip = SocialMediaPost.query.filter_by(api_id=post_id).all()
        if posts_with_clip is None or len(posts_with_clip) == 0:
            continue

        for post in posts_with_clip:
            req = requests.get(f'https://app.ayrshare.com/api/history/{post.api_id}',
                               headers={'Authorization': f'Bearer {api_key}'})
            resp = req.json()

            post_info.append(get_post_data(post, resp))

    from tabulate import tabulate
    click.echo(
        tabulate(post_info, headers=['Platform', 'Type', 'ID', 'Status', 'Created', 'Scheduled', 'Hashtags', 'URL']))


if __name__ == '__main__':
    cli()
