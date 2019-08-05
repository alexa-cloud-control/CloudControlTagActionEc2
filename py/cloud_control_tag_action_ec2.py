""" Lambda function - add/change/remove tag for ec2 """
import boto3

def cloud_control_tag_action_ec2(event, context):
    """ Lambda function - add/change/remove tag for ec2 """

    # validate instance name
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [event["body"]["InstanceName"]]
            }
        ]
    )
    instance_list = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append(instance['InstanceId'])

    if not instance_list:
        msg = "I cannot find the instance with name {}.".format(event["body"]["InstanceName"])
        return {"msg": msg}

    ec2_instance = ec2.instances.filter(InstanceIds=instance_list)
    # validate tag
    tag_response = ec2_client.describe_tags(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [instance_list[0]],
            },
        ],
    )
    tag_status = ""
    tmp_msg = ""
    for tag in tag_response['Tags']:
        if tag['Key'] == event["body"]["TagKey"]:
            if tag['Value'] == event["body"]["TagValue"]:
                tmp_msg = "Tag {} with value {} found.".format(
                    event["body"]["TagKey"], event["body"]["TagValue"]
                )
                tag_status = "tag_match" #0
            else:
                tmp_msg = "tag {} found, but value is different.".format(
                    event["body"]["TagKey"]
                )
                tag_status = "tag_different" #1
        else:
            tag_status = "tag_not_found" #2
            tmp_msg = "Tag {} not found!".format(event["body"]["TagKey"])

    commands = {
        'create_tags': ['create', 'add', 'update', 'change'],
        'delete_tags': ['delete', 'remove']
    }

    action = event["body"]["TagAction"]
    for command_key in commands:
        aliases = commands[command_key]
        if action in aliases:
            if (
                    (command_key == 'create_tags'
                     and tag_status in {'tag_not_found', 'tag_different'})
                    or (command_key == 'delete_tags'
                        and tag_status in {'tag_match', 'tag_different'})
                ):
                    ec2_client.command_key(
                        DryRun=False,
                        Resources=[
                        ec2_instance,
                        ],
                        Tags=[
                            {
                                'Key': event["body"]["TagKey"].capitalize(),
                                'Value': event["body"]["TagValue"]
                            },
                        ]
                    )
                    msg = (
                        "{} Tag key {} for instance {} {}d.".format(
                        tmp_msg,
                        event["body"]["TagKey"].capitalize(),
                        event["body"]["InstanceName"],
                        event["body"]["TagAction"]
                        )
                    )
                    return {"msg": msg}
        
    msg = (
        "I cannot perform {}. "
        "Nothing like this exists in my database."
    ).format(action)
    return {"msg": msg}
