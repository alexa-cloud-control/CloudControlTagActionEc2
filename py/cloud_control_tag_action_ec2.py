""" Lambda function - add/change/remove tag for ec2 """
import boto3
import json

def write_to_dynamo(context):
    """ Write data to DynamoDB table """
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    # function env variable - to change
    context_table = dynamodb_resource.Table('alexa-cloudcontrol-context')
    for context_key, context_value in context.items():
        try:
            context_table.put_item(
                Item={
                    'Element': context_key,
                    'ElementValue': context_value
                }
            )
        except dynamodb_client.exceptions.ClientError as error:
            msg = "Something wrong with my table!"
            print(error)
            return {"msg": msg}
    return 0

def validate_with_dynamo(context):
    """ Read context from DynamoDB table """
    context_list=[
        'the-same',
        'same',
        'like-last-one',
        'like-last-1',
        'last-one',
        'last-1',
        'last',
        'previous',
        'previous-one',
        'previous-1',
        'like-before',
        'like-last-time'
    ]
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    context_table = dynamodb_resource.Table('alexa-cloudcontrol-context')
    function_payload = {}
    # Check if context contains context_list. If yes, check dynamo if there is a value
    # for it. If no, throw error.
    for context_key, context_value in context.items():
        if context_value in context_list:
            try:
                response = context_table.get_item(
                    Key={
                        'Element': context_key
                    }
                )
                function_payload[context_key] = response['Item']['ElementValue']
            except dynamodb_client.exceptions.ClientError as error:
                msg = "I don't remember anything for {}".format(
                    context_key
                )
                print(error)
                return {"msg": msg}
            
        else:
            function_payload[context_key] = context_value
    json_payload = json.dumps(function_payload)
    return json_payload

def cloud_control_tag_action_ec2(event, context):
    """ Lambda function - add/change/remove tag for ec2 """

    msg = ""
    validate_with_context_payload = {
        "LastInstanceName": event["body"]["InstanceName"]
    }
    response = {}
    response = validate_with_dynamo(validate_with_context_payload)
    payload_response = json.loads(response)
    ValidatedInstanceName = payload_response["LastInstanceName"]
    
    # validate instance name
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [ValidatedInstanceName]
            }
        ]
    )
    instance_list = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append(instance['InstanceId'])

    if not instance_list:
        msg = "I cannot find the instance with name {}.".format(ValidatedInstanceName)
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
    # to refactor
    for tag in tag_response['Tags']:
        if tag['Key'] == event["body"]["TagKey"].capitalize():
            if tag['Value'] == event["body"]["TagValue"]:
                tmp_msg = "Tag {} with value {} found.".format(
                    event["body"]["TagKey"].capitalize(), event["body"]["TagValue"]
                )
                tag_status = "tag_match" #0
            else:
                tmp_msg = "tag {} found, but value is different.".format(
                    event["body"]["TagKey"].capitalize()
                )
                tag_status = "tag_different" #1
        else:
            tag_status = "tag_not_found" #2
            tmp_msg = "Tag {} not found!".format(event["body"]["TagKey"].capitalize())

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
                if (command_key == 'create_tags'):
                    ec2_client.create_tags(
                        DryRun=False,
                        Resources=[
                            instance_list[0],
                        ],
                        Tags=[
                            {
                                'Key': event["body"]["TagKey"].capitalize(),
                                'Value': event["body"]["TagValue"]
                            },
                        ]
                    )
                else:
                    ec2_client.delete_tags(
                        DryRun=False,
                        Resources=[
                            instance_list[0],
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
                        ValidatedInstanceName,
                        event["body"]["TagAction"]
                    )
                )
                return {"msg": msg}
    msg = (
        "I cannot perform {}. "
        "Nothing like this exists in my database."
    ).format(action)
    write_to_table_payload = {
        "LastInstanceName": ValidatedInstanceName
    }
    write_to_dynamo(write_to_table_payload)
    return {"msg": msg}
