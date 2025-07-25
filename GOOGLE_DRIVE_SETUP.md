# Google Drive API Setup Guide

## 1. Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

## 2. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details:
   - Name: `arxiv-drive-uploader`
   - Description: `Service account for uploading ArXiv PDFs to Google Drive`
4. Skip role assignment (click "Continue")
5. Click "Done"

## 3. Generate Service Account Key

1. Click on the created service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Download the JSON file
6. Rename it to `service-account-key.json`
7. Place it in the project root directory

## 4. Share Google Drive Folder

1. Create a folder in your Google Drive for the PDFs
2. Right-click the folder > "Share"
3. Add the service account email (found in the JSON file)
4. Give it "Editor" permissions
5. Copy the folder ID from the URL (the part after `/folders/`)

## 5. Install Required Packages

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## 6. Configuration

Update the `DRIVE_FOLDER_ID` in the upload script with your folder ID.

## Security Note

- Keep `service-account-key.json` secure and never commit it to version control
- Add it to `.gitignore`