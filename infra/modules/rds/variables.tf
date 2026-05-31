variable "project_name" {
  description = "Project name used in ContextEngine resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine resource names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable RDS resources."
  type        = map(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs where the PostgreSQL instance can be placed."
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "Security group ID that allows PostgreSQL traffic from ECS tasks."
  type        = string
}

variable "db_name" {
  description = "Initial database name for ContextEngine."
  type        = string
  default     = "contextengine"
}

variable "db_username" {
  description = "Master username for the PostgreSQL instance."
  type        = string
  default     = "context_engine"
}

variable "db_instance_class" {
  description = "RDS instance class used for the low-cost showcase deployment."
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated PostgreSQL storage size in GiB."
  type        = number
  default     = 20
}

variable "backup_retention_period" {
  description = "Automated backup retention period in days."
  type        = number
  default     = 1
}

