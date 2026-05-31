variable "project_name" {
  description = "Project name used in ContextEngine bucket names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine bucket names."
  type        = string
}

variable "account_id" {
  description = "AWS account ID appended to globally unique S3 bucket names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable S3 resources."
  type        = map(string)
}

