import boto3
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure boto3 retry settings
retry_config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'adaptive'  # Uses a retry rate that adapts to the service's throttling behavior
    }
)

# Initialize AWS clients with retry configuration
ec2_client = boto3.client('ec2', config=retry_config)
elbv2_client = boto3.client('elbv2', config=retry_config)
cloudwatch_client = boto3.client('cloudwatch', config=retry_config)

# Get environment variables
DRY_RUN = os.environ.get('DRY_RUN', 'true').lower() == 'true'
LBC_TAG_KEY = os.environ.get('LBC_TAG_KEY', 'kubernetes.io/cluster/')
EXCLUDE_SG_IDS = os.environ.get('EXCLUDE_SG_IDS', '').split(',') if os.environ.get('EXCLUDE_SG_IDS') else []
MAX_ITEMS_PER_RUN = int(os.environ.get('MAX_ITEMS_PER_RUN', '5000'))
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '10'))

# Cache for resource relationships
resource_cache = {}

def get_lbc_security_groups():
    """Get security groups created by EKS LBC using server-side filtering"""
    try:
        security_groups = []
        paginator = ec2_client.get_paginator('describe_security_groups')
        
        # Use server-side filtering where possible
        # We'll use multiple filter combinations to catch different LBC patterns
        filters = [
            # Filter by common LBC tag patterns
            [
                {'Name': 'tag-key', 'Values': [f"{LBC_TAG_KEY}*", "elbv2.k8s.aws/cluster", "ingress.k8s.aws/resource"]}
            ],
            # Filter by name pattern
            [
                {'Name': 'group-name', 'Values': ['k8s-*']}
            ]
        ]
        
        # Try each filter set
        for filter_set in filters:
            page_iterator = paginator.paginate(
                Filters=filter_set,
                PaginationConfig={'MaxItems': MAX_ITEMS_PER_RUN}
            )
            
            for page in page_iterator:
                # Further client-side filtering
                for sg in page['SecurityGroups']:
                    if (is_lbc_security_group(sg) and 
                        sg['GroupId'] not in EXCLUDE_SG_IDS and
                        sg['GroupId'] not in [g['GroupId'] for g in security_groups]):
                        security_groups.append(sg)
                        
                        # If we've reached our limit, stop processing
                        if len(security_groups) >= MAX_ITEMS_PER_RUN:
                            logger.info(f"Reached maximum items per run ({MAX_ITEMS_PER_RUN}). Additional security groups will be processed in future runs.")
                            return security_groups
        
        return security_groups
    except ClientError as e:
        logger.error(f"Error retrieving security groups: {e}")
        raise

def is_lbc_security_group(security_group):
    """Check if a security group was created by EKS LBC"""
    # Check for LBC tags
    if 'Tags' in security_group:
        for tag in security_group['Tags']:
            # LBC typically adds cluster tags to resources it creates
            if tag['Key'].startswith(LBC_TAG_KEY):
                return True
            
            # Additional tag checks for LBC-created resources
            if tag['Key'] == 'elbv2.k8s.aws/cluster' or tag['Key'] == 'ingress.k8s.aws/resource':
                return True
    
    # Check security group name pattern (common for LBC)
    if security_group['GroupName'].startswith('k8s-') and 'alb' in security_group['GroupName'].lower():
        return True
        
    return False

def check_instances_using_sg(sg_id):
    """Check if any EC2 instances are using the security group"""
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        page_iterator = paginator.paginate(
            Filters=[{'Name': 'instance.group-id', 'Values': [sg_id]}]
        )
        
        for page in page_iterator:
            if any(page['Reservations']):
                return True
        return False
    except ClientError as e:
        logger.error(f"Error checking instances for SG {sg_id}: {e}")
        return True  # Assume in use if we can't check

def check_enis_using_sg(sg_id):
    """Check if any ENIs are using the security group"""
    try:
        paginator = ec2_client.get_paginator('describe_network_interfaces')
        page_iterator = paginator.paginate(
            Filters=[{'Name': 'group-id', 'Values': [sg_id]}]
        )
        
        for page in page_iterator:
            if page['NetworkInterfaces']:
                return True
        return False
    except ClientError as e:
        logger.error(f"Error checking ENIs for SG {sg_id}: {e}")
        return True  # Assume in use if we can't check

def check_lbs_using_sg(sg_id):
    """Check if any load balancers are using the security group"""
    try:
        paginator = elbv2_client.get_paginator('describe_load_balancers')
        page_iterator = paginator.paginate()
        
        for page in page_iterator:
            for lb in page['LoadBalancers']:
                if sg_id in lb.get('SecurityGroups', []):
                    return True
        return False
    except ClientError as e:
        logger.error(f"Error checking LBs for SG {sg_id}: {e}")
        return True  # Assume in use if we can't check

def check_sg_references(sg_id):
    """Check if the security group is referenced by other security groups"""
    try:
        # We'll use a more targeted approach to avoid loading all SGs
        paginator = ec2_client.get_paginator('describe_security_groups')
        page_iterator = paginator.paginate(
            Filters=[{'Name': 'ip-permission.group-id', 'Values': [sg_id]}]
        )
        
        for page in page_iterator:
            if page['SecurityGroups']:
                return True
                
        # Check egress rules too
        page_iterator = paginator.paginate(
            Filters=[{'Name': 'egress.ip-permission.group-id', 'Values': [sg_id]}]
        )
        
        for page in page_iterator:
            if page['SecurityGroups']:
                return True
                
        return False
    except ClientError as e:
        logger.error(f"Error checking SG references for SG {sg_id}: {e}")
        return True  # Assume in use if we can't check

def is_security_group_in_use(sg_id):
    """Check if a security group is in use by any resource with caching"""
    try:
        # Check cache first
        if sg_id in resource_cache:
            return resource_cache[sg_id]
        
        # Check EC2 instances
        if check_instances_using_sg(sg_id):
            resource_cache[sg_id] = True
            return True
        
        # Check network interfaces
        if check_enis_using_sg(sg_id):
            resource_cache[sg_id] = True
            return True
        
        # Check load balancers
        if check_lbs_using_sg(sg_id):
            resource_cache[sg_id] = True
            return True
        
        # Check if referenced by other security groups
        if check_sg_references(sg_id):
            resource_cache[sg_id] = True
            return True
        
        resource_cache[sg_id] = False
        return False
    except ClientError as e:
        logger.error(f"Error checking if security group {sg_id} is in use: {e}")
        # If we can't determine, assume it's in use to be safe
        return True

def delete_security_group(sg_id):
    """Delete a security group"""
    try:
        if DRY_RUN:
            logger.info(f"DRY RUN: Would delete security group {sg_id}")
            return True
        else:
            ec2_client.delete_security_group(GroupId=sg_id)
            logger.info(f"Successfully deleted security group {sg_id}")
            return True
    except ClientError as e:
        logger.error(f"Error deleting security group {sg_id}: {e}")
        return False

def process_security_group(sg):
    """Process a single security group"""
    sg_id = sg['GroupId']
    logger.info(f"Processing potential LBC security group: {sg_id} ({sg.get('GroupName', 'N/A')})")
    
    # Check if it's in use
    if not is_security_group_in_use(sg_id):
        logger.info(f"Security group {sg_id} is not in use, proceeding with deletion")
        return delete_security_group(sg_id)
    else:
        logger.info(f"Security group {sg_id} is still in use, skipping")
        return False

def publish_metrics(result):
    """Publish custom CloudWatch metrics"""
    try:
        cloudwatch_client.put_metric_data(
            Namespace='EKSLBCSecurityGroupCleanup',
            MetricData=[
                {
                    'MetricName': 'SecurityGroupsProcessed',
                    'Value': result['total_security_groups_processed'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'SecurityGroupsDeleted',
                    'Value': result['deleted_security_groups'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'ExecutionTime',
                    'Value': result['execution_time_seconds'],
                    'Unit': 'Seconds'
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error publishing metrics: {e}")
        # Don't fail the function if metrics publishing fails

def lambda_handler(event, context):
    """Main Lambda handler function with improved scaling"""
    start_time = time.time()
    logger.info("Starting unused EKS LBC security group cleanup")
    
    try:
        # Get candidate security groups
        security_groups = get_lbc_security_groups()
        logger.info(f"Found {len(security_groups)} potential LBC security groups to process")
        
        deleted_count = 0
        skipped_count = 0
        
        # Process security groups in parallel if there are multiple to process
        if security_groups:
            with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(security_groups))) as executor:
                results = list(executor.map(process_security_group, security_groups))
                
            deleted_count = sum(1 for r in results if r)
            skipped_count = len(results) - deleted_count
        
        execution_time = time.time() - start_time
        result = {
            'total_security_groups_processed': len(security_groups),
            'deleted_security_groups': deleted_count,
            'skipped_security_groups': skipped_count,
            'dry_run': DRY_RUN,
            'execution_time_seconds': execution_time
        }
        
        # Publish metrics
        try:
            publish_metrics(result)
        except Exception as e:
            logger.warning(f"Failed to publish metrics: {e}")
        
        logger.info(f"Cleanup complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        raise
