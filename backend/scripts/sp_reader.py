import logging
import requests
import os
import urllib.parse
import yaml
from collections import deque
from pathlib import Path
from requests_ntlm import HttpNtlmAuth

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
VERIFY = os.environ.get("REQUESTS_CA_BUNDLE", True)
TIMEOUT = (5, 30)
DEPARTMENT = "safety-compliance"
SITE = f"https://companyweb/{DEPARTMENT}"
LIBRARY = "Docs"


def _get_auth():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    sharepoint = config.get("sharepoint", {})
    return HttpNtlmAuth(f"{sharepoint['domain']}\\{sharepoint['user']}", sharepoint["password"])


headers = {"Accept": "application/json;odata=verbose"}

# === ENTRY POINT ===
def list_files(folder_url, local_folder=f"downloaded_files/{DEPARTMENT}", auth=None):
    if auth is None:
        auth = _get_auth()

    collected_files = []
    pending = deque([folder_url])
    while pending:
        current_folder = pending.popleft()
        url = f"{SITE}/_api/web/GetFolderByServerRelativeUrl('{current_folder}')"
        files_url = f"{url}/Files"
        folders_url = f"{url}/Folders"

        # Get files in the folder
        file_resp = requests.get(files_url, auth=auth, headers=headers, verify=VERIFY, timeout=TIMEOUT)
        file_resp.raise_for_status()
        files = file_resp.json()['d']['results']
        for file in files:
            try:
                local_path = download_file(file['ServerRelativeUrl'], local_folder, auth)
                collected_files.append(local_path)
            except Exception as e:
                logging.warning(f"Failed to download {file['ServerRelativeUrl']}: {e}")

        # Get subfolders and queue them instead of recursing
        folder_resp = requests.get(folders_url, auth=auth, headers=headers, verify=VERIFY, timeout=TIMEOUT)
        folder_resp.raise_for_status()
        folders = folder_resp.json()['d']['results']
        for folder in folders:
            name = folder['Name']
            if name not in ("Forms",):  # Skip default system folder
                print("Entering folder:", folder['ServerRelativeUrl'])
                pending.append(folder['ServerRelativeUrl'])

    return collected_files


def download_file(server_relative_url, local_folder, auth):
    file_name = server_relative_url.split('/')[-1]
    encoded_url = urllib.parse.quote(server_relative_url, safe="/").replace("'", "%27")
    file_url = f"{SITE}/_api/web/GetFileByServerRelativeUrl('{encoded_url}')/$value"
    resp = requests.get(file_url, auth=auth, headers=headers, verify=VERIFY, timeout=TIMEOUT)
    resp.raise_for_status()
    os.makedirs(local_folder, exist_ok=True)
    local_path = os.path.join(local_folder, file_name)
    with open(local_path, "wb") as f:
        f.write(resp.content)
    print(f"Downloaded: {local_path}")
    return local_path

# === START ===
if __name__ == "__main__":
    start_folder = f"/{DEPARTMENT}/{LIBRARY}"
    all_files = list_files(start_folder)
    print("All downloaded files:", all_files)