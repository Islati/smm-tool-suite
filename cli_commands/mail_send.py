import csv
import random
import time

import jellyfish
from bs4 import BeautifulSoup
from flask import render_template
from flask_mail import Message
from jinja2 import Environment, BaseLoader
from sqlalchemy import desc
from tqdm import tqdm

from bot.webapp import mail
from bot.webapp.models import MailMessage


def parse_tags(input_text, user_data):
    input_text = input_text.replace("{{full_name}}", user_data["full_name"])
    input_text = input_text.replace("{{email}}", user_data["email"])
    input_text = input_text.replace("{{username}}", user_data["username"])

    return input_text


def check_message_history(cli_bar, user, message,current_message, similarity_max=0.75):
    """
    Check if in all of the history between this user we've sent them a user similar to this one!
    (Easier to check all history than just last one, often times.)
    """
    cli_bar.set_description(f"{user} : Checking message history")

    if message is None:
        return False

    if jellyfish.jaro_winkler_similarity(message, current_message) >= similarity_max:
        return True

    return False


def mail_send(csv_file_location, subject, html_email_template, txt_email_template, skip_duplicates=True,
              check_recent=False, recent_days_check=7, sleep_min=1, sleep_max=5):
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
                email=line[6]
            )

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

        mail_message = MailMessage.query.order_by(desc(MailMessage.id)).first()

        if mail_message is not None and check_message_history(_users, user, mail_message.html, html_email, similarity_max=0.60):
            _users.set_description(f"Skipping {user['email']} as we've sent them a similar message recently.")
            continue

        _users.set_description_str(f"Sending email to {user['full_name']} ({user['email']}")
        msg = Message(
            subject=subject,
            body=text_template_content,  # todo render & replace with jinja2 template
            html=html_email,
            recipients=[user['email']],
            sender=("Islati", "islati@mailtrap.io")
        )

        mail_message = MailMessage(email=user['email'], name=user['full_name'], subject=subject, body=msg.body,
                                   html=msg.html)
        mail_message.save(commit=True)

        try:
            mail.send(msg)
            mail_message.sent = True
        except Exception as e:
            mail_message.sent = False

        mail_message.save(commit=True)
        if not mail_message.sent:
            _users.set_description(f"Failed to send email to {user['full_name']} ({user['email']})")
            time.sleep(3)
            continue

        sleep_time = random.randint(sleep_min, sleep_max)

        _users.set_description(
            f"Sent email to {user['full_name']} ({user['email']})... Sleeping for {sleep_time} seconds")

        time.sleep(sleep_time)
