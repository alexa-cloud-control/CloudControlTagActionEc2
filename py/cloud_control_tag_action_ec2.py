""" Lambda function - add/change/remove tag for ec2 """
import boto3

def cloud_control_state_action_ec2(event, context):
    """ Lambda function - add/change/remove tag for ec2 """




# ------- To refactor

def ec_tags_describe(instance_id, tag_name, tag_value):
    """Check if Tag exists with given value"""
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_tags(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    instance_id,
                ],
            },
        ],
    )
    for tag in response['Tags']:
        if tag['Key'] == tag_name:
            if tag['Value'] == tag_value:
                msg = "Tag {} with value {} found.".format(
                    tag_name, tag_value
                )
                return 0, msg
            else:
                msg = "tag {} found, but value is different".format(
                    tag_name
                )
                return 1, msg
    msg = "Tag {} not found!".format(tag_name)
    return 2, msg

def ec_tag_action(ec_params):
    """Add, remove, update Ec2 tag"""
    ec2_client = boto3.client('ec2')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    msg = ""
    success_code, resource_id = validate_ec2_name(ec_params[0])
    if not success_code == 0:
        msg = "Cannot find instance {}.".format(ec_params[0])
        return 99, msg
    if ec_params[1] == 'create':
        success_code, msg = ec_tags_describe(
            resource_id[0], ec_params[2].capitalize(), ec_params[3]
        )
        if success_code == 2:
            ec2_tag_action = ec2_client.create_tags(
                DryRun=False,
                Resources=[
                    resource_id[0],
                ],
                Tags=[
                    {
                        'Key': ec_params[2].capitalize(),
                        'Value': ec_params[3]
                    },
                ]
            )
        else:
            return 99, msg
    elif ec_params[1] == 'delete':
        success_code, msg = ec_tags_describe(
            resource_id[0], ec_params[2].capitalize(), ec_params[3]
        )
        if not success_code == 0:
            return 1, msg
        ec2_tag_action = ec2_client.delete_tags(
            DryRun=False,
            Resources=[
                resource_id[0],
            ],
            Tags=[
                {
                    'Key': ec_params[2].capitalize(),
                    'Value': ec_params[3]
                },
            ]
        )
    elif ec_params[1] == 'update':
        success_code, msg = ec_tags_describe(
            resource_id[0], ec_params[2].capitalize(), ec_params[3]
        )
        if success_code == 1:
            ec2_tag_action = ec2_client.create_tags(
                DryRun=False,
                Resources=[
                    resource_id[0],
                ],
                Tags=[
                    {
                        'Key': ec_params[2].capitalize(),
                        'Value': ec_params[3]
                    },
                ]
            )
        else:
            return 99, msg
    else:
        msg = "No idea what to do, sorry..."
        return 0, msg
    msg = "Tag key {} for instance {} {}d.".format(
        ec_params[2].capitalize(), ec_params[0], ec_params[1]
    )
    return 0, msg