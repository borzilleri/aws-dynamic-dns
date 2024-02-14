import argparse
import datetime
import ipaddress
import json
import sys
import tomllib
import urllib.request
from pathlib import Path
from pprint import pprint

import boto3
from mypy_boto3_route53 import Route53Client

DEFAULT_PROFILE = "default"
DEFAULT_AWS_REGION = "us-west-2"
DRY_RUN = False
DEBUG_LOG = False
FORCE_COMMIT = False


def _get_config_from_file(filename: str) -> dict:
    config = {}
    with open(filename, "rb") as stream:
        config = tomllib.load(stream)
    return config


def _load_credentials(credentials_file: str, profile: str) -> dict:
    if credentials_file:
        print(f"reading creds file {credentials_file}")
        p = Path(credentials_file)
        if p.is_file():
            with p.open() as f:
                print("loading credntials")
                return json.load(f)
    return {"profile_name": profile}


def _get_route53_client(aws_region: str, credentials: dict) -> Route53Client:
    boto_session = boto3.Session(region_name=aws_region, **credentials)
    return boto_session.client("route53")


def _get_public_ip() -> ipaddress.IPv4Address:
    try:
        response = (
            urllib.request.urlopen("http://checkip.amazonaws.com/")
            .read()
            .decode("utf8")
        )
        ip = ipaddress.ip_address(response.strip())
        print(f"Found public IP Address: {str(ip)}")
        return ip
    except Exception as e:
        print("Error retrieving public IP Address:\n", e)
        sys.exit(1)


def _get_configured_ip(client, zone_id, hostname) -> ipaddress.IPv4Address:
    response = client.test_dns_answer(
        HostedZoneId=zone_id,
        RecordName=hostname,
        RecordType="A",
    )
    if response["RecordData"]:
        ip = ipaddress.ip_address(response["RecordData"][0].strip())
        print(f"{hostname}: Found configured IP Address: {str(ip)}")
        return ip
    else:
        print(f"{hostname}: No configured IP Address found.")
        return None


def _get_timestamp() -> str:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    return utc_now.strftime("%Y-%m-%d %H:%M:%S %Z%z")


def update_dns_record(
    client: Route53Client,
    zone_id: str,
    hostname: str,
    ip: ipaddress.IPv4Address,
    ttl: int,
):
    dns_change_batch = {
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": hostname + ".",
                    "Type": "A",
                    "ResourceRecords": [{"Value": str(ip)}],
                    "TTL": ttl,
                },
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": hostname + ".",
                    "Type": "TXT",
                    "ResourceRecords": [
                        {"Value": f'"Last updated: {_get_timestamp()}"'}
                    ],
                    "TTL": ttl,
                },
            },
        ]
    }
    if DEBUG_LOG:
        pprint(dns_change_batch, indent=2, width=120)
    if not DRY_RUN:
        response = client.change_resource_record_sets(
            HostedZoneId=zone_id, ChangeBatch=dns_change_batch
        )
        pprint(response)
    else:
        print("Dry-Run Enabled. Not committing changes.")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--credentials", "-c")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    config = _get_config_from_file(args.config)
    DRY_RUN = not config["general"]["commit-changes"]
    FORCE_COMMIT = config["general"]["force-commit"]
    DEBUG_LOG = config["general"]["log"]["debug"]
    if DEBUG_LOG:
        pprint(args)
        pprint(config)

    credentials = _load_credentials(
        args.credentials, config["aws"].get("profile", DEFAULT_PROFILE)
    )

    hostname = str(config["dns"]["hostname"])
    zone_id = str(config["dns"]["zone-id"])
    ttl = int(config["dns"]["ttl"])

    r53_client = _get_route53_client(
        config["aws"].get("region", DEFAULT_AWS_REGION), credentials
    )

    public_ip = _get_public_ip()
    host_ip = _get_configured_ip(r53_client, zone_id, hostname)

    if public_ip != host_ip or FORCE_COMMIT:
        print(f"{hostname}: Configuring new IP Address: {str(public_ip)}")
        update_dns_record(r53_client, zone_id, hostname, public_ip, ttl)
    else:
        print(
            f"{hostname}: Configured address matches public address, skipping update."
        )
