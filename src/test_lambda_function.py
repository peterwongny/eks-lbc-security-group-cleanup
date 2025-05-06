import unittest
from unittest.mock import patch, MagicMock
import boto3
import os
from moto import mock_aws
import lambda_function

class TestLambdaFunction(unittest.TestCase):
    @mock_aws
    def test_get_lbc_security_groups(self):
        # Setup
        ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create a security group with LBC tags
        sg = ec2.create_security_group(
            GroupName='k8s-alb-test',
            Description='Test SG for LBC'
        )
        sg_id = sg['GroupId']
        
        ec2.create_tags(
            Resources=[sg_id],
            Tags=[{'Key': 'kubernetes.io/cluster/test-cluster', 'Value': 'owned'}]
        )
        
        # Test
        with patch.object(lambda_function, 'ec2_client', ec2):
            result = lambda_function.get_lbc_security_groups()
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['GroupId'], sg_id)
    
    @mock_aws
    def test_is_lbc_security_group(self):
        # Setup
        ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create a security group with LBC tags
        sg = ec2.create_security_group(
            GroupName='k8s-alb-test',
            Description='Test SG for LBC'
        )
        sg_id = sg['GroupId']
        
        ec2.create_tags(
            Resources=[sg_id],
            Tags=[{'Key': 'kubernetes.io/cluster/test-cluster', 'Value': 'owned'}]
        )
        
        # Get the security group details
        sg_details = ec2.describe_security_groups(GroupIds=[sg_id])['SecurityGroups'][0]
        
        # Test
        result = lambda_function.is_lbc_security_group(sg_details)
        
        # Assert
        self.assertTrue(result)
    
    @mock_aws
    def test_is_security_group_in_use(self):
        # Setup
        ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create a security group
        sg = ec2.create_security_group(
            GroupName='test-sg',
            Description='Test SG'
        )
        sg_id = sg['GroupId']
        
        # Mock the check functions to return False (not in use)
        with patch.object(lambda_function, 'check_instances_using_sg', return_value=False), \
             patch.object(lambda_function, 'check_enis_using_sg', return_value=False), \
             patch.object(lambda_function, 'check_lbs_using_sg', return_value=False), \
             patch.object(lambda_function, 'check_sg_references', return_value=False):
            
            # Test
            result = lambda_function.is_security_group_in_use(sg_id)
        
        # Assert
        self.assertFalse(result)
    
    @mock_aws
    def test_delete_security_group_dry_run(self):
        # Setup
        ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create a security group
        sg = ec2.create_security_group(
            GroupName='test-sg',
            Description='Test SG'
        )
        sg_id = sg['GroupId']
        
        # Set DRY_RUN to True
        lambda_function.DRY_RUN = True
        
        # Test
        with patch.object(lambda_function, 'ec2_client', ec2):
            result = lambda_function.delete_security_group(sg_id)
        
        # Assert
        self.assertTrue(result)
        
        # Verify the security group still exists
        sgs = ec2.describe_security_groups(GroupIds=[sg_id])
        self.assertEqual(len(sgs['SecurityGroups']), 1)

if __name__ == '__main__':
    unittest.main()