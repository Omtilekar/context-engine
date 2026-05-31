variable "project_name" {
  description = "Project name used for tagging AWS resources."
  type        = string
  default     = "context-engine"

  validation {
    condition     = var.project_name == "context-engine"
    error_message = "Project name must remain context-engine to preserve the required AWS name prefix."
  }
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

variable "vpc_cidr" {
  description = "CIDR block for the ContextEngine VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used for public and private subnet placement."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least two availability zones are required."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets that host the ALB and NAT gateway."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly two public subnet CIDR blocks are required."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets that host ECS tasks and RDS."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly two private subnet CIDR blocks are required."
  }
}
