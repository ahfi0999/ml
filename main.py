# Requirements: pip install requests schedule python-dotenv vimeo
import os
import requests
import json
import hashlib
import schedule
import time
from dotenv import load_dotenv
from vimeo import VimeoClient

load_dotenv()
# Credentials from .env file
ZOOM_JWT = os.getenv('ZOOM_JWT')
ZOOM_USER_ID = os.getenv('ZOOM_USER_ID')
VIMEO_CLIENT_ID = os.getenv('VIMEO_CLIENT_ID')
VIMEO_CLIENT_SECRET = os.getenv('VIMEO_CLIENT_SECRET')
VIMEO_ACCESS_TOKEN = os.getenv('VIMEO_ACCESS_TOKEN')
MAPPING_FILE = 'zoom_vimeo_mapping.json'

vimeo = VimeoClient(
    token=VIMEO_ACCESS_TOKEN,
    key=VIMEO_CLIENT_ID,
    secret=VIMEO_CLIENT_SECRET
)

ZOOM_API_URL = f"https://api.zoom.us/v2/users/{ZOOM_USER_ID}/recordings"
HEADERS = {"Authorization": f"Bearer {ZOOM_JWT}"}

# Load or create mapping
if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, 'r') as f:
        mapping = json.load(f)
else:
    mapping = {}

def get_zoom_recordings():
    resp = requests.get(ZOOM_API_URL, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get('meetings', [])

def download_file(download_url, filename):
    token = HEADERS['Authorization'].split(" ")[1]
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(download_url, headers=headers, stream=True)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return filename

def file_hash(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def already_uploaded(zoom_id, file_md5):
    return zoom_id in mapping or file_md5 in [m['file_md5'] for m in mapping.values()]

def upload_to_vimeo(filepath, name):
    uri = vimeo.upload(filepath)
    return uri

def process_recordings():
    print("Checking for new Zoom recordings...")
    meetings = get_zoom_recordings()
    for meeting in meetings:
        meeting_id = str(meeting['id'])
        for file in meeting.get('recording_files', []):
            if not file['status'] == 'completed':
                continue
            download_url = file['download_url']
            filename = f"{meeting_id}_{file['id']}.mp4"
            download_file(download_url, filename)
            md5 = file_hash(filename)
            if already_uploaded(meeting_id, md5):
                print(f"Duplicate found, skipping: {filename}")
                os.remove(filename)
                continue
            try:
                vimeo_uri = upload_to_vimeo(filename, filename)
                mapping[meeting_id] = {'vimeo_uri': vimeo_uri, 'file_md5': md5}
                print(f"Uploaded: {filename} → {vimeo_uri}")
            except Exception as e:
                print(f"Upload failed: {e}")
            os.remove(filename)
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f)

# Run every hour
schedule.every(1).hour.do(process_recordings)
if __name__ == "__main__":
    process_recordings() # Run once immediately
    while True:
        schedule.run_pending()
        time.sleep(60)