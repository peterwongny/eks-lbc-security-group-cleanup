output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.eks_lbc_sg_cleanup.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.eks_lbc_sg_cleanup.function_name
}

output "lambda_role_arn" {
  description = "ARN of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_role.arn
}

output "cloudwatch_event_rule_arn" {
  description = "ARN of the CloudWatch Event Rule"
  value       = aws_cloudwatch_event_rule.schedule.arn
}

output "lambda_log_group" {
  description = "Name of the CloudWatch Log Group for the Lambda function"
  value       = "/aws/lambda/${aws_lambda_function.eks_lbc_sg_cleanup.function_name}"
}
