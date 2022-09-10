import csv
import random
import time
import traceback

import jellyfish
from bs4 import BeautifulSoup
from flask import render_template
from flask_mail import Message
from jinja2 import Environment, BaseLoader
from sqlalchemy import desc
from tqdm import tqdm

from bot.webapp import mail
from bot.webapp.models import MailMessage, Contact, SentMail
from verify_email import verify_email


def parse_tags(input_text, user_data):
    """
    Replaces full_name, email, and username with {{value}} styled tags.
    :param input_text:
    :param user_data:
    :return:
    """
    input_text = input_text.replace("{{full_name}}", user_data["full_name"])
    input_text = input_text.replace("{{email}}", user_data["email"])
    input_text = input_text.replace("{{username}}", user_data["username"])

    return input_text


def check_message_history(cli_bar, user, message, current_message, similarity_max=0.75):
    """
    Check if in all of the history between this user we've sent them a user similar to this one!
    (Easier to check all history than just last one, often times.)
    """
    if message is None:
        return False

    if jellyfish.jaro_winkler_similarity(message, current_message) >= similarity_max:
        return True

    return False


def mail_send(csv_file_location, subject, html_email_template, txt_email_template, skip_duplicates=True,
              check_recent=False, recent_days_check=7, sleep_min=1, sleep_max=5, template_name=None):
    """
    Sends and email to the user.
    :param to_email:
    :param subject:
    :param body:
    :param tags:
    :return:
    """

    user_details = []  # List of dictionaries containing user details
    with open(csv_file_location, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        lines = 0
        for line in csv_reader:
            if lines == 0:
                lines += 1
                continue
            user_info = dict(
                username=line[1],
                full_name=line[2],
                email=line[6],
                bio=line[14],
                instagram_url=line[16],
                business="y" in line[12].lower()
            )

            print(f"Creating user contact for {user_info['email']}")

            contact = Contact(full_name=user_info["full_name"], instagram_url=user_info["instagram_url"],
                              email=user_info["email"], bio=user_info["bio"], business=user_info['business'],
                              valid=verify_email(user_info["email"]))
            contact.save(commit=True)

            user_info['contact'] = contact

            user_details.append(user_info)
            lines += 1

    print(f"Parsed file to find {len(user_details)} users.")

    _users = tqdm(user_details, desc="Sending Emails", unit="emails")
    html_email_template_contents = None
    with open(html_email_template, "r") as f:
        html_email_template_contents = f.read()

    text_template_content = BeautifulSoup(html_email_template_contents, "lxml").text
    jinja_template_render = Environment(loader=BaseLoader()).from_string(html_email_template_contents)
    html_email = jinja_template_render.render()
    for user in _users:
        _users.set_description(f"Checking if we can email {user['email']}")

        sent_mail = SentMail.query.order_by(desc(MailMessage.id)).filter_by(contact_id=user["contact"].id).first()

        if sent_mail is not None and jellyfish.jaro_winkler_similarity(html_email, sent_mail.mail.html) >= 0.75:
            _users.set_description(f"Skipping {user['email']} as we've sent them a similar message recently.")
            continue
        else:
            _users.set_description(f"No past email to {user['email']}")

        _users.set_description_str(f"Sending email to {user['full_name']} ({user['email']}")
        mail_message = MailMessage.query.filter_by(name=template_name).first()

        # Update the html on the cached mail message if there's new html being handed to this template.

        if mail_message is None:
            mail_message = MailMessage(name=template_name, subject=subject, body=text_template_content,
                                       html=html_email)
            mail_message.save(commit=True)

        elif mail_message.html != html_email:
            mail_message.html = html_email
            mail_message.save(commit=True)

        msg = Message(
            subject=subject,
            body=text_template_content,  # todo render & replace with jinja2 template
            html=mail_message.html,
            recipients=[user['email']],
            sender=("Islati", "islati@skreet.ca")
        )

        sent_mail_message = False
        try:
            mail.send(msg)
            sent_mail_record = SentMail(contact=user["contact"], mail=mail_message)
            sent_mail_record.save(commit=True)
            sent_mail_message = True
            _users.set_description("Sent email successfully.")
        except Exception as e:
            trace = traceback.format_exc()
            print(trace)

        mail_message.save(commit=True)
        if not mail_message.sent:
            _users.set_description(f"Failed to send email to {user['full_name']} ({user['email']})")
            time.sleep(3)
            continue

        sleep_time = random.randint(sleep_min, sleep_max)

        _users.set_description(
            f"Sent email to {user['full_name']} ({user['email']})... Sleeping for {sleep_time} seconds")

        time.sleep(sleep_time)
