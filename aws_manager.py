import boto3
from botocore.exceptions import ClientError, ProfileNotFound
import logging
import configparser
import os

logger = logging.getLogger(__name__)

class AWSManager:
    def __init__(self):
        self.ssm_client = None
        self.ec2_client = None
        self.profile = None
        self.region = None
        self.is_connected = False

    def disconnect_profile_and_region(self):
        # Logica per scollegare la sessione attiva se necessario
        pass  # Implementa la logica di disconnessione
    
    def get_profiles(self):
        config = configparser.ConfigParser()
        config.read(os.path.expanduser("~/.aws/credentials"))
        return config.sections()

    def get_regions(self):
        return boto3.session.Session().get_available_regions('ec2')

    def set_profile_and_region(self, profile, region):
        try:
            session = boto3.Session(profile_name=profile, region_name=region)
            self.ssm_client = session.client('ssm')
            self.ec2_client = session.client('ec2')
            self.profile = profile
            self.region = region
            self.is_connected = True
            logger.info(f"Successfully set profile to {profile} and region to {region}")
        except ProfileNotFound:
            self.is_connected = False
            logger.error(f"Profile '{profile}' not found")
            raise ValueError(f"Profile '{profile}' not found")
        except Exception as e:
            self.is_connected = False
            logger.error(f"Error connecting to AWS: {str(e)}")
            raise ValueError(f"Error connecting to AWS: {str(e)}")

    def check_connection(self):
        if self.ec2_client is None:
            logger.warning("EC2 client not initialized")
            return False
        try:
            self.ec2_client.describe_instances(MaxResults=5)
            self.is_connected = True
            logger.debug("AWS connection check successful")
        except Exception as e:
            self.is_connected = False
            logger.error(f"AWS connection check failed: {str(e)}")
        return self.is_connected

    def list_ssm_instances(self):
        if not self.is_connected:
            logger.warning("Attempted to list instances without an active connection")
            return {"error": "Not connected to AWS"}
        try:
            response = self.ssm_client.describe_instance_information()
            instance_ids = [instance['InstanceId'] for instance in response['InstanceInformationList']]
            
            ec2_response = self.ec2_client.describe_instances(InstanceIds=instance_ids)
            instances = []
            for reservation in ec2_response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'id': instance['InstanceId'],
                        'name': next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A'),
                        'type': instance['InstanceType'],
                        'os': instance.get('PlatformDetails', 'N/A'),
                        'state': instance['State']['Name']
                    })
            logger.info(f"Successfully listed {len(instances)} SSM-enabled instances")
            return instances
        except Exception as e:
            logger.error(f"Error listing instances: {str(e)}")
            return {"error": str(e)}

    def start_ssh_session(self, instance_id):
        if not self.is_connected:
            logger.warning("Attempted to start SSH session without an active connection")
            return {"error": "Not connected to AWS"}
        try:
            response = self.ssm_client.start_session(
                Target=instance_id,
                DocumentName='AWS-StartSSHSession'
            )
            logger.info(f"Successfully started SSH session for instance {instance_id}")
            return {"success": True, "sessionId": response['SessionId']}
        except ClientError as e:
            logger.error(f"Failed to start SSH session for instance {instance_id}: {str(e)}")
            return {"error": str(e)}