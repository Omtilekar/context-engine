variable "project_name" {
  description = "Project name used in ContextEngine CloudFront names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine CloudFront names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable CloudFront resources."
  type        = map(string)
}

variable "frontend_bucket_arn" {
  description = "ARN of the private frontend S3 bucket."
  type        = string
}

variable "frontend_bucket_name" {
  description = "Name of the private frontend S3 bucket."
  type        = string
}

variable "frontend_bucket_regional_domain_name" {
  description = "Regional domain name of the private frontend S3 bucket."
  type        = string
}

