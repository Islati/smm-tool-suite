import datetime
import math
import random
from pathlib import Path

import maya
import requests
from moviepy.editor import *
from pytube import YouTube
from pytube.cli import on_progress
import click
import webbrowser

from webapp.models import VideoClip as BotClip, MediaUpload, SocialMediaPost
from ayrshare import SocialPost

api_key = "W8ZMC7Q-PFBMXSB-JPDK8HC-NQPQCXH"
social = SocialPost(api_key)


# function to print all the hashtags in a text
def extract_hashtags(text):
    # initializing hashtag_list variable
    hashtag_list = []

    # splitting the text into words
    for word in text.split():

        # checking the first character of every word
        if word[0] == '#':
            # adding the word to the hashtag_list
            hashtag_list.append(word[1:])

    # printing the hashtag_list
    print("The hashtags in \"" + text + "\" are :")
    for hashtag in hashtag_list:
        print(hashtag)

    return hashtag_list


class VidBot(object):
    """
    Handles the automated process of downloading, chopping, and uploading said video.
    """

    def __init__(self, video_link: str = None, clip_length: int = 33, skip_intro_time: int = 0,
                 output_filename: str = None, post_description: str = None, skip_duplicate_check: bool = False,
                 subclip_start=-1, scheduled_date=None,
                 platforms=["tiktok", "instagram", "twitter", "facebook", "youtube"]):
        self.video_link = video_link
        if video_link is not None:
            self.yt_vid: YouTube = YouTube(video_link, on_progress_callback=on_progress)
        self.downloaded: bool = False
        self.video_path: Path = None
        self.video: VideoFileClip = None
        self.audio: AudioFileClip = None
        self.clip_length = clip_length
        self.clip: VideoFileClip = None
        self.clip_path: Path = None
        self.skip_intro = skip_intro_time
        self.output_filename = output_filename
        self.post_description = post_description
        self.skip_duplicate_check = skip_duplicate_check
        self.subclip_start = subclip_start
        self.scheduled_date = scheduled_date
        self.platforms = platforms

    def check_for_duplicate_clips(self, start_time: int):
        """
        Checks if the video clip already exists in the database by comparing start times.
        :param start_time: start time of the video clip
        :return: True if the clip already exists, False if it does not
        """

        if self.skip_duplicate_check is True:
            return False

        search_clip = BotClip.query.filter_by(start_time=start_time, url=self.video_link).all()

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
        path = self.yt_vid.streams.filter(progressive=True).get_highest_resolution().download()
        self.downloaded = True
        self.video_path = path
        self.video = VideoFileClip(path)
        self.audio = self.video.audio
        return path

    def create_video_clip(self):
        """
        Clips the video to the defined length.
        :param check_duplicates: Check if the clip already exists by comparing start times in the database
        :return: path of the clip
        """

        # if not downloaded then download the clip
        if not self.downloaded:
            self.download_video()

        if os.path.exists(f"{self.output_filename}.mp4"):
            video_clip_record = BotClip(url=self.video_link, title=self.yt_vid.title, start_time=self.subclip_start,
                                        duration=self.clip_length)
            video_clip_record.save(commit=True)

        # get a random start time
        start_time = self.get_random_start_time() if self.subclip_start == -1 else self.subclip_start
        # CHECK FOR DUPLICATE CLIPS IN DB **
        if self.check_for_duplicate_clips(start_time):
            print(f"Duplicate clip starting @ {start_time}s! Retrying...")
            self.create_video_clip()
            return
        end_time = start_time + self.clip_length
        print(f"Clipping video from {start_time}s to {end_time}s")
        # Create & save the clip

        self.clip = self.video.subclip(start_time, end_time)
        audio_clip = self.video.audio.subclip(start_time, end_time)

        self.clip = self.clip.set_audio(audio_clip)
        self.clip.write_videofile(f"{self.output_filename}.mp4", temp_audiofile="tempaudio.m4a", codec="libx264",
                                  audio_codec="aac", remove_temp=False)
        self.clip.close()
        # invoke ffmpeg to append audio subclip.
        import subprocess as sp
        command = ['ffmpeg',
                   '-y',  # approve output file overwite
                   '-i', f"{self.output_filename}.mp4",
                   '-i', "tempaudio.m4a",
                   '-c:v', 'copy',
                   '-c:a', 'aac',  # to convert mp3 to aac
                   '-shortest',
                   f"{self.output_filename}.mp4"]

        print(f"Running command: {' '.join(command)}")
        process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
        process.wait()

        # write the entry to the db
        video_clip_record = BotClip(url=self.video_link, title=self.yt_vid.title, start_time=start_time,
                                    duration=self.clip_length)
        video_clip_record.save(commit=True)

        print(
            f"Created database entry ({video_clip_record.id}) for video clip of {self.yt_vid.title} starting @ {start_time}s")
        return f"{self.output_filename}.mp4", video_clip_record

    def get_random_start_time(self):
        """
        Generate a random start time for the clip.
        Created using the formula:
        r   andom_start_time = random.randint(0 + skip_intro_time, video_duration - clip_length)
        :return:
        """
        return random.randint(0 + self.skip_intro, math.floor(self.video.duration - self.clip_length))

    def upload_clip(self, video_clip: VideoClip):
        """
        Uploads the video clip to social media via the API.
        :return:
        """
        # retrieve the information
        req = requests.get("https://app.ayrshare.com/api/media/uploadUrl",
                           headers={'Authorization': f'Bearer {api_key}'},
                           params={'contentType': 'video/mp4', 'fileName': f"{self.output_filename}.mp4"})

        upload_request_response = req.json()

        media_upload = MediaUpload(access_url=upload_request_response['accessUrl'],
                                   content_type=upload_request_response['contentType'],
                                   upload_url=upload_request_response['uploadUrl'], clip=video_clip)
        media_upload.save(commit=True)

        # upload the video

        req = requests.put(upload_request_response['uploadUrl'],
                           headers={'Content-Type': upload_request_response['contentType']},
                           data=open(f"{self.output_filename}.mp4", 'rb'))

        if req.status_code == 200:
            return media_upload

        print(f"Upload failed with status code {req.status_code}")
        return None

    def upload_to_socials(self, media_upload: MediaUpload):
        """
        Send the video clip to TikTok via the API.
        Does not currently support setting description / hashtags so these will be done via the user when approving the upload inside the official TikTok API.

        :param media_upload:
        :return:
        """
        #
        keywords = extract_hashtags(self.post_description)
        for keyword in self.yt_vid.keywords:
            keywords.append(keyword)

        keywords = list(set(keywords))

        # resp = social.post({
        #     "post": self.post_description,
        #     "platforms": ['tiktok'],
        #     "media_urls": [media_upload.access_url],
        #     "isVideo": True
        # })

        post_data = {
            "post": self.post_description,
            "platforms": self.platforms,
            "media_urls": [media_upload.access_url],
            "isVideo": True,

        }

        if "instagram" in self.platforms:
            post_data["instagramOptions"] = {
                                                "reels": True,
                                                "shareReelsFeed": True,
                                            },

        if "youtube" in self.platforms:
            post_data["youTubeOptions"] = {
                "title": self.yt_vid.title,
                "visibility": "public",
                "tags": keywords,
                "shorts": True,
                "playlistId": "PLZijj4Sp9E9h6pPK3N5NMDLcJ2i2eB-Gt"
            }

        self.scheduled_date = self.find_next_slot(hours_difference=6)

        if self.scheduled_date is not None:
            post_data["scheduleDate"] = self.scheduled_date

        resp = requests.post("https://app.ayrshare.com/api/post", headers={'Authorization': f'Bearer {api_key}'},
                             data=post_data)

        if resp.status_code == 200:
            resp = resp.json()
            print(resp)
            api_id = resp['id']
            print(f"Successfully posted to socials with API ID {api_id}")

            if resp['status'] == 'scheduled':
                print(f"Post scheduled for {self.scheduled_date}")

            for entry in resp['postIds']:
                if entry['status'] != 'success':
                    print(f"Failed to post to {entry['platform']}")
                    continue

                post = SocialMediaPost(api_id=api_id, platform=entry['platform'], post_url=entry['postUrl'],
                                       clip=media_upload.clip)
                post.save(commit=True)

                print(f"Posted to {entry['platform']} with post id {entry['postId']} @ {entry['postUrl']}")
        else:
            print(f"Failed to post to socials with status code {resp.status_code}")
            print(f"Response: {resp.text}")

    def is_slot_ok(self):
        """
        Checks if the slot is ok to post in.
        :return:
        """

        posts_in_slot = SocialMediaPost.query.filter_by(post_time=self.scheduled_date).all()

        if len(posts_in_slot) >= 1:
            return False

    def find_next_slot(self, hours_difference=4):
        """
        Find the next available slot for the video to be posted.
        :return:
        """

        if self.is_slot_ok():
            return self.scheduled_date

        post_time = maya.MayaDT.from_iso8601(self.scheduled_date)
        posts_in_slot = SocialMediaPost.query.filter_by(post_time=self.scheduled_date).all()

        if len(posts_in_slot) >= 1:
            post_time = post_time.add(hours=hours_difference)
            self.scheduled_date = post_time.iso8601()
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

        already_clipped = False

        if os.path.exists(f"{self.output_filename}.mp4"):
            print("Video already exists, skipping download")
            self.downloaded = True
            self.video_path = f"{self.output_filename}.mp4"
            already_clipped = True

        if not self.downloaded:
            self.download_video()
        self.video = VideoFileClip(self.video_path)
        self.downloaded = True

        clip_path, clip_record = None, None
        if not already_clipped:
            print(f"Downloaded {self.yt_vid.title} to {self.video_path} (duration: {self.video.duration})")
            print("Creating video clip!")
            clip_path, clip_record = self.create_video_clip()
            print(f"Created video clip: {clip_path}")
        else:
            clip_path, clip_record = f"{self.output_filename}.mp4", BotClip.query.filter_by(url=self.video_link,
                                                                                            start_time=self.subclip_start,
                                                                                            duration=self.clip_length).first()

        media_file = None  # db record

        if clip_record.upload is None:
            upload = click.prompt("Upload clip to social media? [Y/N] ", type=bool)
            if not upload:
                click.echo("Will not using the created clip")
                if click.prompt("Create a new clip? [Y/N] ", type=bool):
                    self.run()
                    return
                else:
                    exit(0)
                return
            media_file = self.upload_clip(video_clip=clip_record)
        else:
            media_file = clip_record.upload
            click.echo(f"Reusing existing upload {media_file.access_url}")

        try:
            self.upload_to_socials(media_file)
            print(
                "Uploaded clip to YouTube, TikTok, Instagram, Facebook & Twitter! Open your TiKTok app to describe, hashtag & approve the upload.")

        except Exception as e:
            print(f"Failed to upload to socials: {e}")


from webapp import create_app
from webapp.config import Config

flask_app = create_app(Config())


@click.group()
def cli():
    pass


@cli.command()
@click.argument("youtube_url")
@click.option('--length', '-l', "clip_length", default=33, help="Length of the clip in seconds",
              prompt="Length of the clip in seconds")
@click.option('--skip', '-s', "skip_intro_time", default=0, help="Skip the first x seconds of the video",
              prompt="Skip the first x seconds of the video")
@click.option('--output', '-o', "output_filename", default=f"{datetime.datetime.utcnow().timestamp()}",
              help="Output path for the video clip", prompt="Filename for your clip")
@click.option("--description", "-d", "description", prompt="Description for the upload. Should also include hashtags.")
@click.option('--force', '-f', "skip_duplicate_check", default=False,
              help="Force the post of the video, skipping duplicate cuts.")
@click.option('--schedule', '-s', "schedule", is_flag=False, default=maya.now().iso8601(),
              help="Example: 2022-09-05T00:30:00Z")
@click.option('--platforms', '-p', "platforms", is_flag=False, default="tiktok,instagram,facebook,twitter,youtube")
def run(youtube_url: str, clip_length=33, skip_intro_time=0, output_filename: str = None, description: str = None,
        skip_duplicate_check=False, schedule=None, platforms=None):
    bot = VidBot(youtube_url, clip_length=clip_length, skip_intro_time=skip_intro_time, output_filename=output_filename,
                 post_description=description, skip_duplicate_check=skip_duplicate_check, scheduled_date=schedule,
                 platforms=platforms)
    bot.run()


@cli.command('set_upload_schedule')
def set_upload_schedule():
    resp = social.setAutoSchedule({
        'schedule': ['00:00Z', '12:00Z', '16:20Z', '19:00Z', '21:00Z'],
        'title': 'default',
        'setStartDate': '2022-09-04:00:00Z',
    })
    print(resp)


@cli.command('post', help="Post a specific cut of a video to the linked social media accounts")
@click.argument("clip_id")
@click.option('--description', '-d', "description", prompt="Description for the upload. Should also include hashtags.")
@click.option('--force', '-f', "skip_duplicate_check", is_flag=True, default=False,
              help="Force the post of the video, skipping duplicate checks.")
@click.option('--schedule', '-s', "schedule", is_flag=False, default=maya.now().iso8601(),
              help="Example: 2022-09-05T00:30:00Z")
@click.option('--platforms', '-p', "platforms", is_flag=False, default="tiktok,instagram,facebook,twitter,youtube")
def post(clip_id=None, description: str = None, skip_duplicate_check=False, schedule=None, platforms=None):
    clip = BotClip.query.filter_by(id=clip_id).first()

    if clip is None:
        click.echo(f"Could not find clip with id {clip_id}")
        return

    bot = VidBot(clip.url, clip_length=clip.duration, subclip_start=clip.start_time,
                 output_filename=f"clip_{clip_id}_repost", post_description=description,
                 skip_duplicate_check=skip_duplicate_check, scheduled_date=schedule, platforms=platforms)
    bot.run()


if __name__ == '__main__':
    cli()
