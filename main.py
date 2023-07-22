import datetime
import ipaddress
import sys
import tomllib
import urllib
from pprint import pprint

import boto3
from mypy_boto3_route53 import Route53Client

DEFAULT_AWS_REGION = "us-west-2"


def _get_config_from_file(filename: str) -> dict:
    config = {}
    with open(filename, "rb") as stream:
        config = tomllib.load(stream)
    return config


def _get_route53_client(aws_profile: str, aws_region: str) -> Route53Client:
    boto_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
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


if __name__ == "__main__":
    global DRY_RUN
    global DEBUG_LOG

    # get config
    config = _get_config_from_file(sys.argv[1])
    DRY_RUN = not config["general"]["commit-changes"]
    DEBUG_LOG = config["general"]["log"]["debug"]
    if DEBUG_LOG:
        pprint(config)

    hostname = str(config["dns"]["hostname"])
    zone_id = str(config["dns"]["zone-id"])
    ttl = int(config["dns"]["ttl"])

    r53_client = _get_route53_client(
        config["aws"].get("profile", "default"),
        config["aws"].get("region", DEFAULT_AWS_REGION),
    )

    public_ip = _get_public_ip()
    host_ip = _get_configured_ip(r53_client, zone_id, hostname)

    if public_ip == host_ip:
        print(
            f"{hostname}: Configured address matches public address, skipping update."
        )
    else:
        print(f"{hostname}: Configuring new IP Address: {str(public_ip)}")
        update_dns_record(r53_client, zone_id, hostname, public_ip, ttl)
