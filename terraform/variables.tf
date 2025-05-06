variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "EksLbcSecurityGroupCleanup"
}

variable "dry_run" {
  description = "Whether to run in dry run mode (true) or actually delete security groups (false)"
  type        = string
  default     = "true"
}

variable "lbc_tag_key" {
  description = "Tag key prefix used by LBC"
  type        = string
  default     = "kubernetes.io/cluster/"
}

variable "max_items_per_run" {
  description = "Maximum number of security groups to process in a single run"
  type        = string
  default     = "5000"
}

variable "max_workers" {
  description = "Maximum number of concurrent workers for parallel processing"
  type        = string
  default     = "10"
}

variable "exclude_sg_ids" {
  description = "List of security group IDs to exclude from cleanup"
  type        = list(string)
  default     = []
}

variable "schedule_expression" {
  description = "CloudWatch Events schedule expression for triggering the Lambda function"
  type        = string
  default     = "rate(1 day)"
}

variable "schedule_enabled" {
  description = "Whether the CloudWatch Events schedule is enabled"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "List of ARNs to notify when the Lambda function alarms"
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "List of ARNs to notify when the Lambda function alarms return to OK state"
  type        = list(string)
  default     = []
}

variable "enable_high_deletion_alarm" {
  description = "Whether to enable the alarm for high security group deletion counts"
  type        = bool
  default     = false
}

variable "high_deletion_threshold" {
  description = "Threshold for the high deletion count alarm"
  type        = number
  default     = 50
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Terraform   = "true"
    Application = "EksLbcSecurityGroupCleanup"
  }
}
