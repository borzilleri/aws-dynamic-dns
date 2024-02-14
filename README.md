# aws-dynamic-dns

Dynamic DNS update script for AWS Route53. (Yeah, what it says on the tin).

This will use [checkip.amazonaws.com](http://checkip.amazonaws.com) to check the public IP Address of the machine this script is run on. It will compare that to the configured address of the hostname set in the config file. If they differ, it will issue an UPSERT request to AWS to update the A record. Additionally a TXT record will be added indicating the date when the record was last updated by this script.

## Configuraiton

1. Set up AWS IAM User

    Refer to other documentation online, but you will want an IAM user with access to update Route53 information. 
    
2. Set up AWS credentials.

    Create an access key for the IAM user you set up and download/construct a 
    json file with the credential data:
    
```json
{
    "aws_access_key_id": "...",
    "aws_secret_access_key": "..."
}
```

3. Create config.toml

    Copy the [config template](config.template.toml) to `config.toml`, and edit
    it with information appropriate to your aws account.

4. Run the app via the compose file:

```bash
docker compose run --rm app
```

5. (Optional) set up automatic running

    A [plist](io.rampant.aws.dynamicdns.plist) file is included for setting this
    up with launchd on macOS. Simply copy it to `/Library/LaunchDaemons/` and run:

        launchctl load /Library/LaunchDaemons/io.rampant.aws.dynamicdns.plist
    
    Alternately you may use `cron`, or whatever system-specific utilities your OS has.


## TODO

* Support IPv6
* Maybe support arbitrary TXT records/data?
* Multiple zone/records?