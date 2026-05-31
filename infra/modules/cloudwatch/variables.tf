variable "project_name" {
  description = "Project name used in ContextEngine CloudWatch names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine CloudWatch names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable CloudWatch resources."
  type        = map(string)
}

variable "log_group_name" {
  description = "Name of the ECS application log group."
  type        = string
}

