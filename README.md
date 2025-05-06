# EKS LBC Unused Security Group Cleanup

This project provides a Lambda function that identifies and cleans up unused security groups that were created by the EKS Load Balancer Controller (LBC) but weren't properly deleted when the associated ALBs were removed.

## Problem

When the EKS Load Balancer Controller creates ALBs for Kubernetes Ingress resources, it also creates security groups. However, when the ALB is deleted, sometimes these security groups remain, causing you to hit AWS security group limits over time.

## Solution

This Lambda function:
1. Identifies security groups created by the EKS LBC
2. Verifies they are not in use by any resources
3. Safely deletes unused security groups

## Features

- **Parallel Processing**: Uses ThreadPoolExecutor to process multiple security groups concurrently
- **Efficient Resource Filtering**: Implements server-side filtering in AWS API calls
- **Pagination Handling**: Properly handles pagination for all AWS API calls
- **API Throttling Protection**: Uses boto3's built-in retry mechanism with adaptive mode
- **Resource Caching**: Caches resource relationships to avoid repeated API calls
- **Enhanced Monitoring**: Publishes custom CloudWatch metrics for tracking performance and results
- **Safety Features**: Dry run mode, exclusion list, and comprehensive logging

## Repository Structure

```
.
├── README.md                # This file
├── src/
│   └── lambda_function.py   # Lambda function code
├── terraform/               # Terraform configuration for deployment
│   ├── main.tf              # Main Terraform configuration
│   ├── variables.tf         # Variable definitions
│   ├── outputs.tf           # Output definitions
│   ├── versions.tf          # Terraform and provider versions
│   └── terraform.tfvars.example # Example variable values
└── requirements.txt         # Python dependencies
```

## Deployment

### Using Terraform

1. Navigate to the terraform directory:
   ```bash
   cd terraform
   ```

2. Create a `terraform.tfvars` file based on the example:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. Edit `terraform.tfvars` to customize the deployment:
   ```bash
   vim terraform.tfvars
   ```

4. Initialize and apply:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

### Manual Deployment

1. Create a ZIP file with the Lambda function:
   ```bash
   cd src
   zip -r ../function.zip lambda_function.py
   ```

2. Create an IAM role with the necessary permissions:
   - EC2: DescribeSecurityGroups, DescribeInstances, DescribeNetworkInterfaces, DeleteSecurityGroup
   - ELB: DescribeLoadBalancers
   - CloudWatch: PutMetricData, CreateLogGroup, CreateLogStream, PutLogEvents

3. Create the Lambda function using the AWS CLI or Console:
   ```bash
   aws lambda create-function \
     --function-name EksLbcSecurityGroupCleanup \
     --runtime python3.9 \
     --role <IAM_ROLE_ARN> \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://function.zip \
     --timeout 900 \
     --memory-size 1024 \
     --environment "Variables={DRY_RUN=true,LBC_TAG_KEY=kubernetes.io/cluster/,MAX_ITEMS_PER_RUN=5000,MAX_WORKERS=10}"
   ```

4. Set up a CloudWatch Events rule to trigger the function on a schedule.

## Configuration

The Lambda function can be configured using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DRY_RUN` | Set to "true" to log actions without making changes | "true" |
| `LBC_TAG_KEY` | Tag key prefix used by LBC | "kubernetes.io/cluster/" |
| `EXCLUDE_SG_IDS` | Comma-separated list of SG IDs to exclude | "" |
| `MAX_ITEMS_PER_RUN` | Maximum number of security groups to process in a single run | "5000" |
| `MAX_WORKERS` | Maximum number of concurrent workers for parallel processing | "10" |

## Best Practices

1. **Start with Dry Run Mode**: Keep `DRY_RUN=true` initially to observe what would be deleted
2. **Monitor Logs**: Regularly check the CloudWatch Logs for the Lambda function
3. **Set Up Alarms**: Configure CloudWatch Alarms for errors and high deletion counts
4. **Adjust MAX_ITEMS_PER_RUN**: For very large environments, you might want to start with a lower value

## License

This project is licensed under the MIT License - see the LICENSE file for details.
