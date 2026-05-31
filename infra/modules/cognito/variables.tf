variable "project_name" {
  description = "Project name used in ContextEngine Cognito names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine Cognito names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable Cognito resources."
  type        = map(string)
}

