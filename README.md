# Berkowits GMB Automation — Setup Guide

## Phase 1: Google Cloud Setup (one-time)

### 1. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **New Project** → name it `Berkowits GMB Automation`

### 2. Enable APIs
Search for and enable both:
- **Google Business Profile Management API**
- **My Business Account Management API**

### 3. Configure OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Select **External**
3. Fill in:
   - App name: `Berkowits App`
   - Support email: your email
4. Add scope: `https://www.googleapis.com/auth/business.manage`
5. Add yourself as a **Test user**

### 4. Create OAuth Credentials
1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Select **Desktop app**
3. Click **Download JSON** and save as `client_secret.json` in this directory

> `client_secret.json` is in `.gitignore` — it will never be committed.

---

## Phase 2: Run the Scripts

### Install dependencies
```bash
pip install -r requirements.txt
```

### Authenticate (first time only)
```bash
python auth.py
```
A browser window will open. Sign in with the Google account that manages the 49 clinics. A `token.json` file is saved locally for future runs.

### Discover all 49 Location IDs
```bash
# Print to terminal
python discover_locations.py

# Save to location_ids.json + location_ids.csv
python discover_locations.py --save
```

**Sample output:**
```
Account: Berkowits Dental Group (accounts/123)
  49 location(s) found
    [1234567890] Berkowits Dental — Chicago, IL
    [9876543210] Berkowits Dental — Naperville, IL
    ...

Total locations discovered: 49
Saved JSON: location_ids.json
Saved CSV:  location_ids.csv
```

The `location_id` column is the number you need — it maps directly to the GMB reviews URL:
```
https://business.google.com/reviews/l/<location_id>
```

---

## File Reference

| File | Purpose |
|---|---|
| `client_secret.json` | OAuth credentials from Google Cloud (**you provide, not committed**) |
| `token.json` | Saved access token after first auth run (**not committed**) |
| `auth.py` | OAuth 2.0 flow — run once to authenticate |
| `discover_locations.py` | Lists all accounts + locations with their IDs |
| `requirements.txt` | Python dependencies |
