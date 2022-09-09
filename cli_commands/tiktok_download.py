import click

from bot.tiktok import TikTokDownloader


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