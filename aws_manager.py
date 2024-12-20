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
        self.sts_client = None
        self.profile = None
        self.region = None
        self.is_connected = False
        self.account_id = None


    def disconnect_profile_and_region(self):
        pass  
    
    @staticmethod
    def get_profiles():
        """
        Static method to retrieve AWS profiles from credentials file
        Returns: List of profile names or empty list if no profiles found
        """
        try:
            # Get credentials file path
            credentials_path = os.path.expanduser('~/.aws/credentials')
            
            # Check if credentials file exists
            if not os.path.exists(credentials_path):
                logger.warning("AWS credentials file not found")
                return []
            
            # Parse credentials file
            config = configparser.ConfigParser()
            config.read(credentials_path)
            
            # Get profile names (sections in credentials file)
            profiles = config.sections()
            
            logger.info(f"Successfully loaded {len(profiles)} AWS profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting AWS profiles: {str(e)}")
            return []



    def get_regions(self):
        return boto3.session.Session().get_available_regions('ec2')


    def set_profile_and_region(self, profile, region):
        try:
            session = boto3.Session(profile_name=profile, region_name=region)
            self.ssm_client = session.client('ssm')
            self.ec2_client = session.client('ec2')
            self.sts_client = session.client('sts')  # Initialize STS client
            
            # Get AWS account ID
            account_info = self.sts_client.get_caller_identity()
            self.account_id = account_info['Account']
            
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
        """List all EC2 instances with their SSM status"""
        if not self.is_connected:
            logger.warning("Attempted to list instances without an active connection")
            return None

        try:
            # Get all instances with SSM
            ssm_response = self.ssm_client.describe_instance_information()
            # Create a set of instance IDs that have SSM
            ssm_instance_ids = {instance['InstanceId'] for instance in ssm_response.get('InstanceInformationList', [])}
            logger.debug(f"Found {len(ssm_instance_ids)} instances with SSM: {ssm_instance_ids}")
            
            # Get all EC2 instances
            instances = []
            paginator = self.ec2_client.get_paginator('describe_instances')
            
            for page in paginator.paginate():
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        # Explicitly check if the instance ID is in the SSM set
                        has_ssm = instance_id in ssm_instance_ids
                        
                        instance_data = {
                            'id': instance_id,
                            'name': next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A'),
                            'type': instance['InstanceType'],
                            'os': instance.get('PlatformDetails', 'N/A'),
                            'state': instance['State']['Name'],
                            'has_ssm': has_ssm  # Boolean value indicating if instance has SSM
                        }
                        logger.debug(f"Instance {instance_id} has_ssm: {has_ssm}")
                        instances.append(instance_data)
            
            # Sort instances: SSM instances first, then by name
            instances.sort(key=lambda x: (not x['has_ssm'], x.get('name', '').lower()))
            
            logger.info(f"Successfully listed {len(instances)} instances (with SSM: {len(ssm_instance_ids)})")
            return instances
            
        except Exception as e:
            logger.error(f"Error listing instances: {str(e)}")
            if 'ExpiredTokenException' in str(e):
                self.is_connected = False  # Set connection status to false
                return {'error': 'Authentication token expired. Please reconnect.'}
            return None
        
    def get_instance_details(self, instance_id):
        """
        Get detailed information about a specific EC2 instance
        
        Args:
            instance_id (str): The ID of the EC2 instance
            
        Returns:
            dict: Detailed information about the instance or None if an error occurs
        """
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                logger.warning(f"No instance found with ID: {instance_id}")
                return None
                
            instance = response['Reservations'][0]['Instances'][0]
            
            # Get instance IAM role if it exists
            iam_role = ''
            if instance.get('IamInstanceProfile'):
                iam_role = instance['IamInstanceProfile'].get('Arn', '').split('/')[-1]
            
            # Get security group names
            security_groups = [sg['GroupName'] for sg in instance.get('SecurityGroups', [])]
            
            instance_details = {
                'id': instance['InstanceId'],
                'name': next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A'),
                'platform': instance.get('PlatformDetails', 'N/A'),
                'public_ip': instance.get('PublicIpAddress', 'N/A'),
                'private_ip': instance.get('PrivateIpAddress', 'N/A'),
                'vpc_id': instance.get('VpcId', 'N/A'),
                'subnet_id': instance.get('SubnetId', 'N/A'),
                'iam_role': iam_role,
                'ami_id': instance.get('ImageId', 'N/A'),
                'key_name': instance.get('KeyName', 'N/A'),
                'security_groups': ', '.join(security_groups) if security_groups else 'N/A'
            }
            
            logger.debug(f"Retrieved details for instance {instance_id}")
            return instance_details
            
        except Exception as e:
            logger.error(f"Error getting instance details: {str(e)}")
            return None
        
        
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