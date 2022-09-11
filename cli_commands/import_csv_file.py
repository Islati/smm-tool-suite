"""
Imports a CSV file into the database.
Retrieved from instagram scraper of public emails.

Other formats can be supported by modifying the code below.
"""
import csv

from bot.services.email_validator import EmailValidator
from bot.webapp.models import Contact


def scan_folder_for_csv_files(folder_location):
    """
    Scans a folder for CSV files and returns a list of the files.
    :param folder_location:
    :return:
    """
    import os
    import glob

    user_details = []

    csv_files = glob.glob(os.path.join(folder_location, "*.csv"))
    print(f"Found {len(csv_files)} CSV files in {folder_location}.")
    for file in csv_files:
        print(f"~ Parsing {file}...")
        try:
            user_details += import_csv_file_command(csv_file_location=file)
        except:
            print(f"~ Failed to parse {file} due to error.. Skipping...")
            continue
    return user_details


def import_csv_file_command(csv_file_location):
    user_details = []  # List of dictionaries containing user details
    duplicate_user = 0
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

            print(f"Creating user contact for {user_info['email']}...")

            contact = Contact.query.filter_by(email=user_info['email']).first()

            if contact is not None:
                duplicate_user += 1
                continue

            print(f"~ Validating email address {user_info['email']}...")
            verified_email = EmailValidator.validate(user_info['email'])

            contact = Contact(full_name=user_info["full_name"], instagram_url=user_info["instagram_url"],
                              email=user_info["email"], bio=user_info["bio"], business=user_info['business'],
                              valid=verified_email)
            contact.save(commit=True)

            print(f"~Created contact {contact.email} with valid email: {contact.valid}")

            user_info['contact'] = contact

            user_details.append(user_info)
            lines += 1

    print(
        f"Parsed file to find {len(user_details)} users.\nDuplicate Information of {duplicate_user} users already exists in the database.\n + {len(user_details)} users added to the database.")
    return user_details
