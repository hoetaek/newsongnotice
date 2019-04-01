import boto3
from botocore.exceptions import ClientError

def change_ip():
    instance_id = 'i-0cee15f71341f0fa8'
    client = boto3.client('ec2')
    current_allocation_id = client.describe_addresses()['Addresses'][0]['AllocationId']
    try:
        allocation = client.allocate_address(Domain='vpc')
        client.associate_address(AllocationId=allocation['AllocationId'],
                                 InstanceId=instance_id)
        client.release_address(AllocationId=current_allocation_id)

    except ClientError as e:
        print(e)