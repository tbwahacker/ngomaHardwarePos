# myapp/management/commands/backup_database.py

from django.core.management.base import BaseCommand
from pathlib import Path
from datetime import datetime
import shutil
import googleapiclient.discovery
import google_auth_oauthlib.flow
import google.auth.transport.requests
import os

DATABASE_PATH = Path.home() / '.ngomahardware' / 'db.sqlite3'
BACKUP_DIR = Path.home() / '.ngomahardware' / 'backups'


class Command(BaseCommand):
    help = 'Backup database and upload to Google Drive'

    def handle(self, *args, **kwargs):
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True)

        current_month = datetime.now().strftime("%Y-%m")
        month_backup_dir = BACKUP_DIR / current_month
        if not month_backup_dir.exists():
            month_backup_dir.mkdir(parents=True)

        backup_file = month_backup_dir / f'db_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.sqlite3'
        shutil.copy(DATABASE_PATH, backup_file)
        print(backup_file)
        self.upload_to_google_drive(backup_file, current_month)

    def upload_to_google_drive(self, file_path, folder_name):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file('static/client_secret_ngomahardware1.json',
                                                                                   SCOPES)
        creds = flow.run_local_server(port=0)
        service = googleapiclient.discovery.build('drive', 'v3', credentials=creds)

        # Check if folder exists, create if not
        folder_id = self.get_drive_folder_id(service, folder_name)
        if not folder_id:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')

        # Upload file to Google Drive
        file_metadata = {
            'name': file_path.name,
            'parents': [folder_id]
        }
        media = googleapiclient.http.MediaFileUpload(file_path, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    def get_drive_folder_id(self, service, folder_name):
        results = service.files().list(q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                                       spaces='drive', fields='files(id, name)').execute()
        folders = results.get('files', [])
        if folders:
            return folders[0].get('id')
        return None
