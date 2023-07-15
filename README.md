# aws-dynamic-dns

Dynamic DNS update script for AWS Route53. (Yeah, what it says on the tin).

## Configuraiton

1. Set up AWS IAM User

    Refer to other documentation online, but you will want an IAM user with access to update Route53 information. 
    
2. Set up AWS credentials.

    Create an access key for the IAM user you set up and configure your aws credentials file with a profile and that key. Use a distinct profile name like `aws-dynamic-dns`

3. Copy the [config template](config.template.toml) to `config.toml` somewhere and 
edit it with your information.

4. Run the script

        pipenv run python3 main.py /path/to/config.toml