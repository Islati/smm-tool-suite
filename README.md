# Social Manager (CLI)
Complete social media automation suite.

## Features


### Automated shortform video content.
```python
$ python cli.py run --help
```
* Youtube Downloader
* Tiktok Downloader
* Use local video files
* Optional ffmpeg video encoding
* Define platforms for repost.
* Scheduling posts for 'in 2 hours' (human language)
* Random segments or specify a segment with its start time and duration.

### Recreate previously created clips
_ Mess up? That's fine. Recreate a clip. _
```python
$ python cli.py redo_clip --help
```


### Image Posting
```python
$ python cli.py image --help
```
* Download & Repost
* Customizable description
* Scheduling
* Duplicate content prevention

## Tiktok Downloader (Watermark optional)
```python
$ python cli.py tiktok_download <url> <output_file_name>
```

## Media Management
* View downloaded images, videos `python cli.py images`
* Overview of created posts. `python cli.py history --help` _(many options)_
* View created clips (videos) `python cli.py clips`

## Post History
```python
$ python cli.py history --help
```

* View posts in the last X Days
* View posts in the next X Days
* View the last X created posts.

## Post Info
```python
$ python cli.py post_info --help
```

* View information on a post via its clip_id, image_id, or url.

## Mass emails & Templating

*Creating an email template* 
```python
$ python cli.py add-email-template --help
```

*Deleting an email template*
```python
$ python cli.py delete-email-template --help
```
*Viewing an email template*
```python
$ python cli.py view-email-templates
```

*Test an email being sent*
```python
$ python cli.py test_mail
```

*Prepare & Deliver mail messages*
```python
$ python cli.py mail --help
```

# Mass CSV Import
```python
$ python cli.py import-csv-contents --help
```

# Fully featured web GUI (built with Vue.js)
```python
$ python cli.py gui
```
