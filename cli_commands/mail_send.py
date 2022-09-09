import csv
from mailbox import Message

from tqdm import tqdm

from bot.webapp import mail


def parse_tags(input_text, user_data):
    input_text = input_text.replace("{{full_name}}", user_data["full_name"])
    input_text = input_text.replace("{{email}}", user_data["email"])
    input_text = input_text.replace("{{username}}", user_data["username"])

    return input_text

def mail_send(csv_file_location,subject,email_template, skip_duplicates=True, check_recent=False, recent_days_check=7):
    """
    Sends and email to the user.
    :param to_email:
    :param subject:
    :param body:
    :param tags:
    :return:
    """

    user_details = [] # List of dictionaries containing user details
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

    print(f"Preparing to email {len(user_details)} users.")

    _users = tqdm(user_details, desc="Sending Emails", unit="emails")
    for user in _users:
        _users.set_description_str(f"Sending email to {user['full_name']} ({user['email']}")
        msg = Message(
            subject=parse_tags(subject,user),
            body=None, # todo render & replace with jinja2 template
            recipients=[user['email']],
            sender=None
        )

        mail.send(msg)

