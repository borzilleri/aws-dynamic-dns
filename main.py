import sys
import yaml
import boto3
import urllib
import datetime
import time


def _get_config_from_file(filename):
    config = {}
    with open(filename, "r") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    return config


def _get_route53_client(aws_profile):
    boto_session = boto3.Session(profile_name=aws_profile)
    return boto_session.client("route53")


def _get_public_ip():
    try:
        public_ip = (
            urllib.request.urlopen("http://checkip.amazonaws.com/")
            .read()
            .decode("utf8")
        )
        return public_ip.strip()
    except:
        return None


def _get_configured_ip(client, zone_id, hostname):
    response = client.test_dns_answer(
        HostedZoneId=zone_id,
        RecordName=hostname,
        RecordType="A",
    )
    if response["RecordData"]:
        return response["RecordData"][0]
    else:
        return None


def _get_timestamp():
    now_utc = datetime.utcfromtimestamp(int(time.time))
    return now_utc.strftime("%Y-%m-%d %H:%M:%S %Z%z")


def host_needs_update(client, zone_id, hostname, public_ip):
    host_ip = _get_configured_ip(client, zone_id, hostname)
    if host_ip is None:
        print("{}: No ip configured.".format(hostname))
    else:
        print("{}: Configured ip is {}".format(hostname, host_ip))
    return host_ip != public_ip


def update_dns_record(client, zone_id, hostname, ip, ttl):
    print("{}: Updating IP address.".fpormat(hostname))
    dns_change_batch = {
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": hostname + ".",
                    "Type": "A",
                    "ResourceRecords": [{"Value": ip}],
                    "TTL": ttl,
                },
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": hostname + ".",
                    "Type": "TXT",
                    "ResourceRecords": [
                        {"Value": '"Last updated: {}"'.format(_get_timestamp())}
                    ],
                    "TTL": ttl,
                },
            },
        ]
    }
    print(dns_change_batch)
    response = client.change_resource_record_sets(
        HostedZoneId=zone_id, ChangeBatch=dns_change_batch
    )
    return response


if __name__ == "__main__":
    # get config
    config = _get_config_from_file(sys.argv[1])
    # print("Current configuration:\n", yaml.dump(config, default_flow_style=False))

    # config variables
    aws_profile = config["aws"]["profile"]
    default_ttl = config["aws"]["default-ttl"]

    # Get our current public ip.
    public_ip = _get_public_ip()
    if public_ip is None:
        print("Error retrieving public ip.")
        sys.exit(1)
    else:
        print("Public IP is: {}".format(public_ip))

    # start boto Session
    r53_client = _get_route53_client(aws_profile)

    for zone_name, zone in config["zones"].items():
        print("Updating hosts in zone: {} ({})".format(zone_name, zone["zone-id"]))
        for host in zone["hosts"]:
            print("Checking host: {}", host["hostname"])
            needs_update = host_needs_update(
                r53_client, zone["zone-id"], host["hostname"], public_ip
            )
            if needs_update:
                update_dns_record(
                    zone["zone-id"],
                    host["hostname"],
                    public_ip,
                    host.get("ttl", default_ttl),
                )
