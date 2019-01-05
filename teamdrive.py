from __future__ import print_function
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import Error
from httplib2 import Http
from oauth2client import file, client, tools
import logging
import mimetypes
import os


class TeamDrive(object):
    """methods and functins for working with Googles Drive API"""

    SCOPES = 'https://www.googleapis.com/auth/drive.file'
    store = ''
    creds = ''
    drive_api = ''
    file_exists = False
    file_id = ''

    def __init__(self, file_name=None, folder_id=None):
        self.file_name = file_name
        self.teamdrive_folder_id = folder_id
        self.store = file.Storage('token.json')
        self.creds = self.store.get()        
        self.__file_exists(self.file_name)
        #self.__save_to_google_drive()


    def __save_to_google_drive(self):
        """ Saves a file to  Google Drive

        Uploads a file to the specified Google Drive folder.

        Args: 
            None

        Returns:
            None

        """
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if not self.creds or self.creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', self.SCOPES)
            creds = tools.run_flow(flow, self.store)
        
        #Now build our api object, thing
        self.drive_api = build('drive', 'v3', credentials=self.creds)

        # documents_saved 0 : error and 1: success
        documents_saved = 0

        # get the file name of the document
        doc_name = os.path.basename(self.file_name)

        # set the metadata
        file_metadata = {'name': doc_name, 'parents': [self.teamdrive_folder_id]} 
        
        media = MediaFileUpload(self.file_name, mimetype='application/pdf')     # setting the mimetype needs to be dynamic
        try:
            if self.file_exists:
                # update
                savefile = self.drive_api.files().update(body=file_metadata, fileId=self.file_id, media_body=media, supportsTeamDrives=True, fields='id,spaces,webViewLink,version').execute()
                documents_saved = 1
                logging.info('TeamDrive Update: ' + doc_name + ' to: ' + self.teamdrive_folder_id + ' file id: ' + savefile.get('id') + ' url: ' + savefile.get('webViewLink'))
                print("Created file id: '%s'." % (savefile.get('id')))
            else:
                # create
                savefile = self.drive_api.files().create(body=file_metadata, media_body=media, supportsTeamDrives=True, fields='id,spaces,webViewLink,version').execute()
                documents_saved = 1
                logging.info('TeamDrive Created: ' + doc_name + ' to: ' + self.teamdrive_folder_id + ' file id: ' + savefile.get('id') + ' url: ' + savefile.get('webViewLink'))
        except Error as ge:
            logging.error('Google Drive Exception: ' + ge)
            print(ge)

        return documents_saved

    def __file_exists(self, file_name=None):
        """ Checks for the existence of a file on the Team Drive

        Determines by performing an exact match search on the file name if the file already
        exists on the Team Drive. If it finds the file the file_exists flag is set to true
        and the file_id is set to the returned fileId

        Args
            file_name (str): the name of the file including the extension

        Returns
            None

        """
        page_token = None
        file_name = 'name=\'' + os.path.basename(self.file_name) + '\''
        self.drive_api = build('drive', 'v3', credentials=self.creds)

        try:
            while True:
                response = self.drive_api.files().list(q=file_name, includeTeamDriveItems=True, supportsTeamDrives=True, fields='nextPageToken, files(id, name)', pageToken=page_token).execute()
                for file in response.get('files', []):
                    self.file_id = file.get('id')
                    self.file_exists = True
                    # Process change
                    print('Found file: %s (%s)' % (file.get('name'), file.get('id')))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except Error as ge:
            logging.error('Google Drive Exception: ' + ge.content)
            print(ge)

                    



