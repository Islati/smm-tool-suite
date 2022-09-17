# function to print all the hashtags in a text
import mimetypes
import os
import shutil
import subprocess as sp
from itertools import islice

import requests
from pytube import YouTube

from bot import VideoClip, ImageDb, MediaUpload, TikTokDownloader

from flask import current_app


def compile_keywords(post_description: str = None, youtube_video: YouTube = None, tiktok_video: TikTokDownloader = None,
                     character_limit=400):
    """
    Compile the keywords (hashtags) for this vid. Uses the provided description, and any online source if available.
    :return:
    """

    if post_description is None and youtube_video is None and tiktok_video is None:
        return None

    keywords = []

    if post_description:
        keywords = extract_hashtags(post_description)
    keyword_length = 0

    for keyword in keywords:
        keyword_length += len(keyword)
        if keyword_length >= character_limit:
            break

    if youtube_video is not None:
        for keyword in youtube_video.keywords:
            if keyword_length >= character_limit or len(keyword) + keyword_length >= character_limit:
                break

            keywords.append(keyword.replace("#", ""))
            keyword_length += len(keyword)

    if tiktok_video is not None:
        for keyword in tiktok_video.hashtags:
            if keyword_length >= character_limit or len(keyword) + keyword_length >= character_limit:
                break

            keywords.append(keyword)
            keyword_length += len(keyword)

    keywords = list(set(keywords))
    return keywords


def is_image_file(file):
    if file is None:
        return False
    return 'image' in mimetypes.guess_type(file)[0]


def is_video_file(file):
    """
    Checks if the file is a video file.
    :param file:
    :return:
    """
    if file is None:
        return False

    mimetype = mimetypes.guess_type(file)[0]
    return "video" in mimetype or 'gif' in mimetype


def post_to_socials(local_file_name, title, description, media_upload: MediaUpload, platforms):
    """
    Send the video clip to TikTok via the API.
    Does not currently support setting description / hashtags so these will be done via the user when approving the upload inside the official TikTok API.

    :param media_upload:
    :return:
    """

    date_time = None

    _is_video_file = is_video_file(local_file_name)

    platform_defaults = current_app.config.get('PLATFORM_DEFAULTS')

    compiled_keyword_list = compile_keywords(post_description=media_upload.clip.description)

    post_data = {}
    # post to each social platform one by one,
    for platform in platforms.split(','):
        post_data = {
            "post": f"{description}",
            "platforms": platform,
            "mediaUrls": [media_upload.access_url],
            "isVideo": is_video_file,
            "shortenLinks": False,
            "requiresApproval": False,
        }

        # todo image alt text on media platforms being set.

        # Match the platforms we're
        # with the default values for that platform.
        match platform:
            case "twitter":
                pass
            case "facebook":
                pass
            case "instagram":
                pass
            case "tiktok":
                pass
            case "youtube":
                post_data["youTubeOptions"] = {
                    "title": media_upload.title,
                    "post": post_data['post'],
                    "tags": compiled_keyword_list,
                    "visibility": platform_defaults['youtube']['visibility'] if 'visibility' in platform_defaults[
                        'youtube'].keys() else "public",
                    # todo IMPLEMENT THUMBNAIL CUSTOMIZATION
                    "thumbNail": thumbnail_url,
                    "madeForKids": False,
                    "shorts": True,
                }
    case
    "instagram":
    if 'post' in platform_defaults['instagram'].keys():
        post_data['post'] = self.parse_tags(platform_defaults['instagram']['post'])[0:2200]
    if self.is_video_file(filename):
        post_data["instagramOptions"] = {
            "reels": True,
            "shareReelsFeed": True,
        }
    case
    "youtube":
    if 'post' in platform_defaults['youtube'].keys():
        post_data['post'] = self.parse_tags(platform_defaults['youtube']['post'])

    thumbnail_url = None

    if self.youtube_video_download_link is not None:
        thumbnail_url = self.yt_vid.thumbnail_url

    if self.tiktok_video_url is not None:
        thumbnail_url = self.tiktok_downloader.thumbnail_url

    post_data["youTubeOptions"] = {
        "title": self.post_title[0:100],
        "post": post_data['post'],
        "tags": compiled_keyword_list,
        "visibility": platform_defaults['youtube']['visibility'] if 'visibility' in platform_defaults[
            'youtube'].keys() else "public",
        # todo IMPLEMENT THUMBNAIL CUSTOMIZATION
        "thumbNail": thumbnail_url,
        "madeForKids": False,
        "shorts": True,
    }

    if post_data['youTubeOptions']['thumbNail'] is None:
        del post_data['youTubeOptions']['thumbNail']
    case
    "facebook":
    if 'post' in platform_defaults['facebook'].keys():
        post_data['post'] = self.parse_tags(platform_defaults['facebook']['post'])

    post_data['faceBookOptions'] = {
        "altText": self.parse_tags(platform_defaults['facebook']['altText']),
        "mediaCaptions": self.parse_tags(platform_defaults['facebook']['mediaCaptions']),
    }

    if is_video_file:
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
        print('post emails trimmed to  {}'.format(len(post_data['post'])))
    # Post the request to AYRShare.
    resp = requests.post("https://app.ayrshare.com/api/post",
                         headers={'Authorization': f'Bearer {self.application_config.MAILTRAP_API_KEY}'},
                         json=post_data)
    if resp.status_code == 200:
        resp = resp.json()
        api_id = resp['id']

        if resp['status'] == 'scheduled':
            post = SocialMediaPost(api_id=api_id, platform=platform, media_upload=media_upload,
                                   post_time=date_time.datetime(
                                       to_timezone="UTC") if date_time is not None else datetime.datetime.utcnow(),
                                   hashtags=compiled_keyword_list, )
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


def upload_file_to_cloud(local_file_path, video_clip: VideoClip = None, image: ImageDb = None):
    """
    Uploads the file to the cloud.
    :param output_file_name:
    :param local_file_path:
    :param video_clip:
    :param image:
    :return:
    """
    assert video_clip is not None or image is not None, "No video clip or image provided to upload."

    content_type = None

    try:
        content_type = mimetypes.guess_type(local_file_path)[0]
    except:
        pass

    if content_type is None:
        raise Exception(f"Could not determine content type for file")

    # retrieve the information
    req = requests.get("https://app.ayrshare.com/api/media/uploadUrl",
                       headers={'Authorization': f'Bearer {current_app.config.get("MAILTRAP_API_KEY")}'},
                       params={'contentType': content_type,
                               'fileName': f"{local_file_path}"})

    upload_request_response = req.json()

    print(f"File URL: {upload_request_response['accessUrl']}")

    if image is not None:
        media_upload = MediaUpload(access_url=upload_request_response['accessUrl'],
                                   content_type=upload_request_response['contentType'],
                                   upload_url=upload_request_response['uploadUrl'], image=image)
    else:
        media_upload = MediaUpload(access_url=upload_request_response['accessUrl'],
                                   content_type=upload_request_response['contentType'],
                                   upload_url=upload_request_response['uploadUrl'], clip=video_clip)
    media_upload.save(commit=True)

    # upload the video

    req = requests.put(upload_request_response['uploadUrl'],
                       headers={'Content-Type': upload_request_response['contentType']},
                       data=open(f"{local_file_path}", 'rb'))

    if req.status_code == 200:
        return media_upload

    print(f"Upload failed with status code {req.status_code}")
    return None


def download_image(image_url, output_filename):
    """
    Downloads the image from the URL
    :return:
    """
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        with open(output_filename, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
            return output_filename

    return None


def chunk(arr_range, arr_size):
    arr_range = iter(arr_range)
    return iter(lambda: tuple(islice(arr_range, arr_size)), ())


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


def ffmpeg_convert_to_mp4(filename, targetname=None):
    command = [
        'ffmpeg',
        '-i', filename,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-vf', 'format=yuv420p',
        '-movflags', '+faststart',
        '-y', targetname
    ]

    # command = ['ffmpeg',
    #            '-y',  # approve output file overwite
    #            '-i', f"clip_{self.output_filename}",
    #            '-i', f"tempaudio.m4a",
    #            '-c:v', 'copy',
    #            '-c:a', 'aac',  # to convert mp3 to aac
    #            '-shortest',
    #            f"{self.output_filename}"]

    process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    process.wait()


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    """ Makes a new video file playing video file ``filename`` between
        the times ``t1`` and ``t2``. """
    name, ext = os.path.splitext(filename)
    if not targetname:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    # Convert & Subclip.
    command = [
        'ffmpeg',
        '-i', filename,
        '-c:v', 'copy',
        '-c:a', 'copu',
        '-movflags', '+faststart',
        '-ss', "%0.2f" % t1,
        "-t", "%0.2f" % (t2 - t1),
        '-y', targetname
    ]

    # command = ['ffmpeg',
    #            '-y',  # approve output file overwite
    #            '-i', f"clip_{self.output_filename}",
    #            '-i', f"tempaudio.m4a",
    #            '-c:v', 'copy',
    #            '-c:a', 'aac',  # to convert mp3 to aac
    #            '-shortest',
    #            f"{self.output_filename}"]

    process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    process.wait()
    #
    # cmd = [get_setting("FFMPEG_BINARY"), "-y",
    #        "-i", filename,
    #        "-ss", "%0.2f" % t1,
    #        "-map", "0", "-vcodec", "h264", "-acodec", "aac", targetname]

    # subprocess_call(cmd)
