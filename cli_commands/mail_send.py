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

from bot.services.email_validator import EmailValidator
from bot.webapp import mail
from bot.webapp.models import MailMessage, Contact, SentMail

from cli_commands.import_csv_file import import_csv_file_command


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


def mail_send(template, skip_duplicates=True,
              check_recent=False, recent_days_check=7, sleep_min=1, sleep_max=5, csv_file_location=None):
    """
    Sends and email to the user.
    :param to_email:
    :param subject:
    :param body:
    :param tags:
    :return:
    """

    mail_message = MailMessage.query.filter_by(name=template).first()
    if mail_message is None:
        print(
            f"Template with name {template} not found.\nView available templates by running 'python cli.py view-email-templates'")
        return

    user_details = []  # List of dictionaries containing user details

    # If we're given a csv file then import it.
    if csv_file_location is not None:
        user_details = import_csv_file_command(csv_file_location=csv_file_location)
    else:
        contacts = Contact.query.order_by(desc(Contact.id)).all()
        _contact_iteration = tqdm(contacts, desc=f"Loading ({len(contacts)}) contacts from database...")
        for contact in contacts:
            user_details.append({
                "full_name": contact.full_name,
                "email": contact.email,
                "username": contact.username,
                "contact": contact,
                "bio": contact.bio,
                "instagram_url": contact.instagram_url,
                "business": contact.business,
            })
            _contact_iteration.set_description(f"+ {contact.email}")

    _users = tqdm(user_details, desc="Sending Emails", unit="emails")

    text_template_content = BeautifulSoup(mail_message.html, "lxml").text
    jinja_template_render = Environment(loader=BaseLoader()).from_string(mail_message.html)
    html_email = jinja_template_render.render()
    for user in _users:
        if not user['contact'].verified_email:
            contact = user['contact']

            # This contact is invalid, skip it. Not verified, but checked.
            if contact.updated_at > contact.created_at:
                continue

            # Verify the email address.
            # Non-valid emails can be detected by checking verified_email=False and updated_at > created_at
            _users.set_description(f"Verifying email: {contact.email}")
            valid = EmailValidator.validate(contact.email)

            if not valid:
                contact.verified_email = False
                contact.save(commit=True)
                _users.set_description(f"Skipping {user['email']} (invalid email)")
                continue

            contact.verified_email = True
            contact.save(commit=True)

        _users.set_description(f"Checking message history for {user['email']}..")

        # Check & validate user again before sending.
        # if not verify_email(user['email']):
        #     user['contact'].valid = False
        #     user['contact'].save(commit=True)
        #     _users.set_description(f"Skipping {user['email']} (invalid email)")
        #     continue

        sent_mail = SentMail.query.order_by(desc(MailMessage.id)).filter_by(contact_id=user["contact"].id).first()

        if sent_mail is not None and jellyfish.jaro_winkler_similarity(html_email, sent_mail.mail.html) >= 0.75:
            _users.set_description(f"Skipping {user['email']} as we've sent them a similar message recently.")
            continue

        _users.set_description_str(f"Sending email to {user['full_name']} ({user['email']}")

        msg = Message(
            subject=mail_message.subject,
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
            _users.set_description(f"+ Email to {user['email']}")
        except Exception as e:
            trace = traceback.format_exc()
            print(trace)

        mail_message.save(commit=True)
        if not sent_mail_message:
            _users.set_description(f"Failed to send email to {user['full_name']} ({user['email']})")
            time.sleep(3)
            continue

        sleep_time = random.randint(sleep_min, sleep_max)

        _users.set_description(
            f"Sent email to {user['full_name']} ({user['email']})... Sleeping for {sleep_time} seconds")

        time.sleep(sleep_time)
