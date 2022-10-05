from __future__ import print_function

import io
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

"""
My Google Drive was using 15.4 GB. My limit is 15
This was mostly taken up from images and videos from a trip to Lebanon in 2017
There were also a duplicate of each of these files, sometimes two
Moving these files by hand were a pain, since the page had to refresh every ~50 files
So I made this script, which locates these files, copies and saves them locally, and moves the ones in Drive to trash
Then I can empty trash in Drive
Now I have just 3.5 GB of storage used
"""

SCOPES = ['https://www.googleapis.com/auth/drive']

def trashFile(service, id):
    file = service.files().get(fileId=id, fields="trashed").execute()
    file['trashed'] = True
    service.files().update(body=file, fileId=id).execute()

def saveFile(file, path):
    if not os.path.exists(path):
        with open(path, 'wb') as loc:
            loc.write(file.getvalue())
            loc.close()

def copyFile(service, id):
    request = service.files().get_media(fileId=id)
    fd = io.BytesIO()
    downloader = MediaIoBaseDownload(fd=fd, request=request)

    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fd

def main():
    creds = None

    # If already authorized
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If not autherized
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for next time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Create directory to store files
    dir = "./DriveDownloadedLocally2"
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    try:
        service = build('drive', 'v3', credentials=creds)
        page_token = None

        copied = 0
        deleted = 0
        while True:
            # Query the files
            # Store next page token for next iteration so that every page is searched
            response = service.files().list(q="(mimeType contains 'image/' or mimeType contains 'video/') and modifiedTime < '2020-01-01T12:00:00' and 'me' in owners", 
                                            spaces='drive',
                                            fields='nextPageToken, files(id, name)',
                                            pageToken=page_token).execute()
            
            # Just for debugging
            for file in response.get('files', []):
                id = file.get("id")
                name = file.get("name")
                path = os.path.join(dir, name)

                # If image wasn't already saved
                if not os.path.exists(path):
                    cf = copyFile(service=service, id=id)
                    saveFile(file=cf, path=path)

                    print(F'Downloaded file: {name}')
                    copied += 1

                # Delete the file we copied
                DELETE = True
                if DELETE:
                    trashFile(service=service, id=id)
                    print(F'Trashed file: {name}')
                    deleted += 1
            
            # Assign next page
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
            
        print(F'Copied a total of {copied} files')
        print(F'Deleted a total of {deleted} files')

    except HttpError as error:
        print(f'Error: {error}')


if __name__ == '__main__':
    main()