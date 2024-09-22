import os
import sqlite3
import time
import random
from collections import Counter
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# Set the scopes and credentials file
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
CREDS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
DB_FILE = 'email_senders.db'  # SQLite database file


def get_service():
    """Authenticates and returns the Gmail service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    print(f"Granted Scopes after authorization: {creds.scopes}")

    service = build('gmail', 'v1', credentials=creds)
    return service, creds


def create_table():
    """Creates the blocked_senders table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked_senders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT,
            sender_email TEXT,
            folder_label TEXT,
            email_count INTEGER
        )
    ''')
    conn.commit()
    conn.close()


def insert_or_update_sender(sender_name, sender_email, folder_label, email_count):
    """Inserts or updates the sender information in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if the sender already exists in the database
    cursor.execute('''
        SELECT id, email_count FROM blocked_senders 
        WHERE sender_email = ? AND folder_label = ?
    ''', (sender_email, folder_label))
    result = cursor.fetchone()

    if result:
        # Update the existing record by increasing the email count
        new_count = result[1] + email_count
        cursor.execute('''
            UPDATE blocked_senders
            SET email_count = ?
            WHERE id = ?
        ''', (new_count, result[0]))
    else:
        # Insert a new record for the sender
        cursor.execute('''
            INSERT INTO blocked_senders (sender_name, sender_email, folder_label, email_count)
            VALUES (?, ?, ?, ?)
        ''', (sender_name, sender_email, folder_label, email_count))

    conn.commit()
    conn.close()


def get_sender_email(message):
    """Extracts the sender's email and name from a message."""
    try:
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header.get('name') == 'From':
                sender = header.get('value')
                # Parse the sender information to separate name and email
                name, email = parse_sender(sender)
                return name, email
    except Exception as e:
        print(f"Error extracting sender email: {e}")
    return None, None


def parse_sender(sender_str):
    """Parses the sender string into name and email."""
    if '<' in sender_str and '>' in sender_str:
        name, email = sender_str.split('<')
        name = name.strip().replace('"', '')
        email = email.strip('>')
        return name, email
    return None, sender_str


def fetch_senders_in_label(service, user_id, label_id, label_name, start_page=1, end_page=None):
    """Fetches all unique email senders from the specified label, with pagination control by page range."""
    print(f"Fetching messages from {label_name} folder...")

    # Calculate total messages in the label
    total_messages = get_total_messages(service, user_id, label_id)
    total_pages = (total_messages // 500) + 1
    print(f"Total messages in {label_name}: {total_messages} ({total_pages} pages)")

    # Set end_page to total pages if not provided
    if end_page is None:
        end_page = total_pages

    # Fetch messages only for the specified range of pages
    messages = get_messages(service, user_id, label_id, start_page=start_page, end_page=end_page)

    # Clear sender list to avoid duplicates between runs
    senders = []

    for message_meta in messages:
        # Fetch the full message to retrieve the sender
        message = service.users().messages().get(userId=user_id, id=message_meta['id'], format='metadata').execute()
        sender_name, sender_email = get_sender_email(message)
        if sender_email:
            senders.append(sender_email)

    unique_senders = Counter(senders)
    print(f"\nUnique senders in the {label_name} folder:")
    for sender_email, count in unique_senders.items():
        print(f"Sender: {sender_email}, Count: {count}")
        # Insert the sender info into the database
        insert_or_update_sender(sender_name, sender_email, label_name, count)


def get_total_messages(service, user_id, label_id):
    """Returns the total number of messages in a label."""
    response = service.users().labels().get(userId=user_id, id=label_id).execute()
    return response['messagesTotal']


def get_messages(service, user_id, label_id, start_page=1, end_page=None):
    """Fetches messages in a given label within the specified page range."""
    messages = []
    next_page_token = None
    page_count = 0

    try:
        while True:
            response = service.users().messages().list(
                userId=user_id, 
                labelIds=[label_id], 
                pageToken=next_page_token, 
                maxResults=500
            ).execute()

            if 'messages' in response:
                page_count += 1
                if start_page <= page_count <= end_page:
                    messages.extend(response['messages'])

            next_page_token = response.get('nextPageToken')

            if page_count >= end_page or not next_page_token:
                break
    except HttpError as error:
        print(f"An error occurred while fetching messages: {error}")

    return messages


def main():
    user_id = 'me'
    
    print("Getting Gmail service...")
    service, creds = get_service()

    # Create the database table if it doesn't exist
    create_table()

    # Fetch and print label info (total message count per label)
    labels = service.users().labels().list(userId=user_id).execute()
    label_map = {label['name']: label['id'] for label in labels['labels']}

    # Fetch and store senders from the Spam folder
    if 'SPAM' in label_map:
        spam_label_id = label_map['SPAM']
        fetch_senders_in_label(service, user_id, spam_label_id, 'SPAM', start_page=1, end_page=1)  # Single fetch
    else:
        print("Error: Spam folder not found.")

    # Fetch and store senders from the Inbox folder, specifying the page range
    if 'INBOX' in label_map:
        inbox_label_id = label_map['INBOX']
        fetch_senders_in_label(service, user_id, inbox_label_id, 'INBOX', start_page=1, end_page=3)  # 3 pages
    else:
        print("Error: Inbox folder not found.")

    print("Done!")


if __name__ == '__main__':
    main()
