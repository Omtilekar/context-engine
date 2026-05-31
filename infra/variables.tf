variable "project_name" {
  description = "Project name used for tagging AWS resources."
  type        = string
  default     = "context-engine"
}

variable "environment" {
  description = "Deployment environment for AWS resources."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "staging"], var.environment)
    error_message = "Environment must be either prod or staging."
  }
}

variable "aws_region" {
  description = "AWS region where all ContextEngine resources are deployed."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "ContextEngine must be deployed in us-east-1."
  }
}

variable "aws_profile" {
  description = "AWS CLI profile used for Terraform operations."
  type        = string
  default     = "context-engine-admin"
}

variable "account_id" {
  description = "AWS account ID that owns ContextEngine infrastructure."
  type        = string
  default     = "256716302630"
}

