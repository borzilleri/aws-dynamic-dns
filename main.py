import datetime
import ipaddress
import sys
import tomllib
import urllib
from pprint import pprint

import boto3
from mypy_boto3_route53 import Route53Client


def _get_config_from_file(filename: str) -> dict:
    config = {}
    with open(filename, "rb") as stream:
        config = tomllib.load(stream)
    return config


def _get_route53_client(aws_profile) -> Route53Client:
    boto_session = boto3.Session(profile_name=aws_profile)
    return boto_session.client("route53")


def _get_public_ip() -> ipaddress.IPv4Address:
    try:
        public_ip = (
            urllib.request.urlopen("http://checkip.amazonaws.com/")
            .read()
            .decode("utf8")
        )
        return ipaddress.ip_address(public_ip.strip())
    except Exception as e:
        print("Error retrieving public ip:\n", e)
        sys.exit(1)


def _get_configured_ip(client, zone_id, hostname) -> ipaddress.IPv4Address:
    response = client.test_dns_answer(
        HostedZoneId=zone_id,
        RecordName=hostname,
        RecordType="A",
    )
    if response["RecordData"]:
        return ipaddress.ip_address(response["RecordData"][0])
    else:
        return None


def _get_timestamp() -> str:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    return utc_now.strftime("%Y-%m-%d %H:%M:%S %Z%z")


def host_needs_update(
    client: Route53Client, zone_id: str, hostname: str, public_ip: ipaddress.IPv4Address
) -> bool:
    host_ip = _get_configured_ip(client, zone_id, hostname)
    if host_ip is None:
        print(f"{hostname}: No ip configured.")
    else:
        print(f"{hostname}: Configured ip is {host_ip}")
    return host_ip != public_ip


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
        pprint(dns_change_batch, indent=2, compact=True)
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

    public_ip = _get_public_ip()
    r53_client = _get_route53_client(config["aws"]["profile"])

    hostname = str(config["dns"]["hostname"])
    zone_id = str(config["dns"]["zone-id"])
    ttl = int(config["dns"]["ttl"])

    print(f"{hostname}: checking configured ip.")
    needs_update = host_needs_update(r53_client, zone_id, hostname, public_ip)
    if needs_update:
        print(f"{hostname}: configuring new ip: {public_ip}")
        update_dns_record(r53_client, zone_id, hostname, public_ip, ttl)
    else:
        print(f"{hostname}: configured ip has not changed, skipping.")
