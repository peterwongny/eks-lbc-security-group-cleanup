# EKS LBC Security Group Cleanup - Terraform

This Terraform configuration deploys the EKS Load Balancer Controller (LBC) Security Group Cleanup Lambda function, which identifies and cleans up unused security groups created by the EKS LBC.

## Architecture

The deployment includes:

1. **Lambda Function**: Identifies and cleans up unused security groups
2. **IAM Role and Policies**: Provides necessary permissions for the Lambda function
3. **CloudWatch Event Rule**: Schedules regular execution of the Lambda function
4. **CloudWatch Alarms**: Monitors for errors and high deletion counts

## Prerequisites

- Terraform >= 1.0.0
- AWS CLI configured with appropriate permissions
- AWS provider >= 4.0.0

## Usage

1. Clone the repository and navigate to the terraform directory:

```bash
cd /path/to/clean_unused_sg_eks_lbc/terraform
```

2. Create a `terraform.tfvars` file based on the example:

```bash
cp terraform.tfvars.example terraform.tfvars
```

3. Edit `terraform.tfvars` to customize the deployment:

```bash
vim terraform.tfvars
```

4. Initialize Terraform:

```bash
terraform init
```

5. Plan the deployment:

```bash
terraform plan
```

6. Apply the configuration:

```bash
terraform apply
```

## Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region to deploy resources in | `us-east-1` |
| `function_name` | Name of the Lambda function | `EksLbcSecurityGroupCleanup` |
| `dry_run` | Whether to run in dry run mode | `"true"` |
| `lbc_tag_key` | Tag key prefix used by LBC | `kubernetes.io/cluster/` |
| `max_items_per_run` | Maximum number of security groups to process in a single run | `"5000"` |
| `max_workers` | Maximum number of concurrent workers | `"10"` |
| `exclude_sg_ids` | List of security group IDs to exclude from cleanup | `[]` |
| `schedule_expression` | CloudWatch Events schedule expression | `rate(1 day)` |
| `schedule_enabled` | Whether the CloudWatch Events schedule is enabled | `true` |
| `alarm_actions` | List of ARNs to notify when alarms trigger | `[]` |
| `ok_actions` | List of ARNs to notify when alarms return to OK | `[]` |
| `enable_high_deletion_alarm` | Whether to enable the high deletion count alarm | `false` |
| `high_deletion_threshold` | Threshold for the high deletion count alarm | `50` |
| `tags` | Tags to apply to all resources | See `variables.tf` |

## Outputs

| Output | Description |
|--------|-------------|
| `lambda_function_arn` | ARN of the Lambda function |
| `lambda_function_name` | Name of the Lambda function |
| `lambda_role_arn` | ARN of the IAM role used by the Lambda function |
| `cloudwatch_event_rule_arn` | ARN of the CloudWatch Event Rule |
| `lambda_log_group` | Name of the CloudWatch Log Group for the Lambda function |

## Best Practices

1. **Start with Dry Run Mode**: Keep `dry_run = "true"` initially to observe what would be deleted
2. **Adjust MAX_ITEMS_PER_RUN**: For very large environments, you might want to start with a lower value
3. **Set Up Notifications**: Configure `alarm_actions` to receive notifications about errors
4. **Monitor Logs**: Regularly check the CloudWatch Logs for the Lambda function

## Cleanup

To remove all resources created by this Terraform configuration:

```bash
terraform destroy
```
