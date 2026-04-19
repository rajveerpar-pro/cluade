"""
Discover all GMB Location IDs across all accounts.

Usage:
  python discover_locations.py              # print to terminal
  python discover_locations.py --save       # also save to location_ids.json + location_ids.csv

The script calls two APIs:
  1. mybusinessaccountmanagement  -> accounts.list()
  2. mybusinessbusinessinformation -> locations.list(parent=account)
"""

import argparse
import csv
import json
import sys

import googleapiclient.discovery
from auth import get_credentials

ACCOUNT_MGMT_API = "mybusinessaccountmanagement"
ACCOUNT_MGMT_VERSION = "v1"
BIZ_INFO_API = "mybusinessbusinessinformation"
BIZ_INFO_VERSION = "v1"

LOCATION_READ_MASK = (
    "name,title,storefrontAddress,websiteUri,phoneNumbers"
)


def build_services(creds):
    account_svc = googleapiclient.discovery.build(
        ACCOUNT_MGMT_API,
        ACCOUNT_MGMT_VERSION,
        credentials=creds,
        discoveryServiceUrl=(
            f"https://{ACCOUNT_MGMT_API}.googleapis.com/$discovery/rest"
            f"?version={ACCOUNT_MGMT_VERSION}"
        ),
    )
    biz_svc = googleapiclient.discovery.build(
        BIZ_INFO_API,
        BIZ_INFO_VERSION,
        credentials=creds,
        discoveryServiceUrl=(
            f"https://{BIZ_INFO_API}.googleapis.com/$discovery/rest"
            f"?version={BIZ_INFO_VERSION}"
        ),
    )
    return account_svc, biz_svc


def list_accounts(account_svc) -> list[dict]:
    accounts = []
    page_token = None
    while True:
        resp = account_svc.accounts().list(pageToken=page_token).execute()
        accounts.extend(resp.get("accounts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return accounts


def list_locations(biz_svc, account_name: str) -> list[dict]:
    locations = []
    page_token = None
    while True:
        resp = (
            biz_svc.accounts()
            .locations()
            .list(
                parent=account_name,
                readMask=LOCATION_READ_MASK,
                pageToken=page_token,
            )
            .execute()
        )
        locations.extend(resp.get("locations", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return locations


def extract_location_id(resource_name: str) -> str:
    """'locations/123456789' -> '123456789'"""
    return resource_name.split("/")[-1]


def run(save: bool = False):
    print("Authenticating...")
    creds = get_credentials()

    print("Building API clients...")
    account_svc, biz_svc = build_services(creds)

    print("Fetching accounts...")
    accounts = list_accounts(account_svc)
    if not accounts:
        print("No accounts found. Make sure the authenticated user manages GMB accounts.")
        sys.exit(1)
    print(f"  Found {len(accounts)} account(s).\n")

    all_locations = []

    for account in accounts:
        account_name = account["name"]
        account_display = account.get("accountName", account_name)
        print(f"Account: {account_display} ({account_name})")

        locations = list_locations(biz_svc, account_name)
        print(f"  {len(locations)} location(s) found")

        for loc in locations:
            location_id = extract_location_id(loc["name"])
            title = loc.get("title", "N/A")
            address_parts = loc.get("storefrontAddress", {}).get("addressLines", [])
            city = loc.get("storefrontAddress", {}).get("locality", "N/A")
            state = loc.get("storefrontAddress", {}).get("administrativeArea", "N/A")

            entry = {
                "account_name": account_display,
                "account_resource": account_name,
                "location_id": location_id,
                "location_resource": loc["name"],
                "title": title,
                "address": ", ".join(address_parts),
                "city": city,
                "state": state,
                "gmb_reviews_url": f"https://business.google.com/reviews/l/{location_id}",
            }
            all_locations.append(entry)

            print(
                f"    [{location_id}] {title} — {city}, {state}"
            )

    print(f"\nTotal locations discovered: {len(all_locations)}")

    if save:
        json_path = "location_ids.json"
        csv_path = "location_ids.csv"

        with open(json_path, "w") as f:
            json.dump(all_locations, f, indent=2)
        print(f"Saved JSON: {json_path}")

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_locations[0].keys())
            writer.writeheader()
            writer.writerows(all_locations)
        print(f"Saved CSV:  {csv_path}")

    return all_locations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover GMB location IDs")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to location_ids.json and location_ids.csv",
    )
    args = parser.parse_args()
    run(save=args.save)
