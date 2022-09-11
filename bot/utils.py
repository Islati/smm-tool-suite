# function to print all the hashtags in a text
import os
import subprocess as sp
from itertools import islice


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
