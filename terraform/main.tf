provider "aws" {
  region = var.aws_region
}

#####################################
# Lambda Function
#####################################

# Archive the Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_function.py"
  output_path = "${path.module}/function.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "eks_lbc_sg_cleanup" {
  function_name    = var.function_name
  description      = "Lambda function for cleaning up unused security groups created by EKS LBC with built-in boto3 retry"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  timeout          = 900
  memory_size      = 1024

  environment {
    variables = {
      DRY_RUN           = var.dry_run
      LBC_TAG_KEY       = var.lbc_tag_key
      MAX_ITEMS_PER_RUN = var.max_items_per_run
      MAX_WORKERS       = var.max_workers
      EXCLUDE_SG_IDS    = join(",", var.exclude_sg_ids)
    }
  }

  tags = var.tags
}

#####################################
# IAM Role and Policies
#####################################

# Create IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Create policy for EC2 and ELB permissions
resource "aws_iam_policy" "ec2_elb_policy" {
  name        = "${var.function_name}-ec2-elb-policy"
  description = "Policy for EC2 and ELB permissions needed by the Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeInstances",
          "ec2:DescribeNetworkInterfaces",
          "elasticloadbalancing:DescribeLoadBalancers",
          "ec2:DeleteSecurityGroup"
        ]
        Resource = "*"
      }
    ]
  })
}

# Create policy for CloudWatch metrics
resource "aws_iam_policy" "cloudwatch_metrics_policy" {
  name        = "${var.function_name}-cloudwatch-metrics-policy"
  description = "Policy for CloudWatch metrics permissions needed by the Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Create policy for CloudWatch logs
resource "aws_iam_policy" "cloudwatch_logs_policy" {
  name        = "${var.function_name}-cloudwatch-logs-policy"
  description = "Policy for CloudWatch logs permissions needed by the Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach policies to the Lambda role
resource "aws_iam_role_policy_attachment" "ec2_elb_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.ec2_elb_policy.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_metrics_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.cloudwatch_metrics_policy.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs_policy.arn
}

#####################################
# CloudWatch Event Rule (Scheduler)
#####################################

# Create CloudWatch Event Rule to trigger the Lambda function on a schedule
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.function_name}-schedule"
  description         = "Schedule for triggering the EKS LBC security group cleanup Lambda function"
  schedule_expression = var.schedule_expression
  is_enabled          = var.schedule_enabled

  tags = var.tags
}

# Set the Lambda function as the target for the CloudWatch Event Rule
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "TriggerLambda"
  arn       = aws_lambda_function.eks_lbc_sg_cleanup.arn
}

# Grant permission for CloudWatch Events to invoke the Lambda function
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.eks_lbc_sg_cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}

#####################################
# CloudWatch Alarms
#####################################

# Create CloudWatch Alarm for high error rates
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "This alarm monitors for errors in the EKS LBC security group cleanup Lambda function"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions

  dimensions = {
    FunctionName = aws_lambda_function.eks_lbc_sg_cleanup.function_name
  }

  tags = var.tags
}

# Create CloudWatch Alarm for high deletion counts (optional)
resource "aws_cloudwatch_metric_alarm" "high_deletion_count" {
  count               = var.enable_high_deletion_alarm ? 1 : 0
  alarm_name          = "${var.function_name}-high-deletion-count"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "SecurityGroupsDeleted"
  namespace           = "EKSLBCSecurityGroupCleanup"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.high_deletion_threshold
  alarm_description   = "This alarm monitors for unusually high security group deletion counts"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions

  tags = var.tags
}
