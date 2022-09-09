import csv


def mail_send(csv_file_location, skip_duplicates, check_recent=False, recent_days_check=7):
    """
    Sends and email to the user.
    :param to_email:
    :param subject:
    :param body:
    :param tags:
    :return:
    """

    user_details = {}
    with open(csv_file_location, 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        for line in csv_reader:
            print(line)


    # msg = Message(
    #     subject=subject,
    #     body=body,
    #     recipients=[to_email],
    #     sender=app.config['MAIL_DEFAULT_SENDER']
    # )

    # mail.send(msg)

