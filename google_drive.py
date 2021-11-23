from apiclient import discovery
from apiclient.http import MediaFileUpload
from google.oauth2 import service_account
import googleapiclient.discovery

from utils import ( hex_to_rgb )

class GoogleDrive(object):

    def __init__(self, service_account_file):
        credentials = self._get_credentials(service_account_file)
        self.drive_service = self._get_drive_instance(credentials)
        self.docs_service = self._get_docs_instance(credentials)

    def _get_credentials(self, service_account_file):

        SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents'
        ]

        credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)

        return credentials

    def _get_drive_instance(self, credentials):
        return discovery.build('drive', 'v3', credentials=credentials)

    def _get_docs_instance(self, credentials):
        return discovery.build('docs', 'v1', credentials=credentials)

    def create_folder(name, folder_parent_id):
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents':[folder_parent_id]
        }

        return service.files().create(body=folder_metadata).execute()

    def upload_media(full_filepath, mimetype, folder_parent_id):
        file_metadata = {
            'name': full_filepath,
            'parents':[folder_parent_id]
        }

        media = MediaFileUpload(full_filepath, mimetype='image/jpeg')
        return drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    def create_document(name, folder_parents_id):
        file_metadata = {
            'name': name,
            'mimeType':'application/vnd.google-apps.document',
            'parents':[folder_parents_id]
        }

        return drive_service.files().create(body=file_metadata).execute()

    def get_end_cursor_position(self, document_id):
        result = docs_service.documents().get(documentId=document_id).execute()
        return result.get('body')['content'][-1]['endIndex'] - 1

    def write_document(self, document_id, body, is_bold = False, rgb_hex = '000000'):
        PIXELS_IN_8BIT_COLOR = 256
        body_length = len(body)
        red, green, blue = hex_to_rgb(rgb_hex)

        start_index = get_end_cursor_position(document_id)
        end_index = start_pos + body_length

        requests = [
             {
                'insertText': {
                    'location': {
                        'index': start_index,
                    },
                    'text': '{}\n\n'.format(body)
                },

            },
            {
                'updateTextStyle': {
                    'textStyle': {
                        'bold': is_bold,
                        'weightedFontFamily': {
                            'fontFamily': 'Arial'
                        },
                        'foregroundColor': {
                            'color': {
                                'rgbColor': {
                                    'red': red/PIXELS_IN_8BIT_COLOR,
                                    'green': green/PIXELS_IN_8BIT_COLOR,
                                    'blue': blue/PIXELS_IN_8BIT_COLOR
                                }
                            }
                        }
                    },
                    'range': {
                        'startIndex': start_index,
                        'endIndex': end_index
                    },
                    'fields': 'bold, weightedFontFamily, foregroundColor'
                }
            }
        ]

        return docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
