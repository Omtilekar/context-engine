variable "project_name" {
  description = "Project name used in ContextEngine resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment used in ContextEngine resource names."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all taggable ECS resources."
  type        = map(string)
}

variable "aws_region" {
  description = "AWS region used by the backend container."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ECS and ALB resources are deployed."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the application load balancer."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS Fargate tasks."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for the public application load balancer."
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS Fargate tasks."
  type        = string
}

variable "desired_count" {
  description = "Desired number of ECS tasks while infrastructure is idle."
  type        = number
  default     = 0
}

variable "container_port" {
  description = "Port exposed by the FastAPI backend container."
  type        = number
  default     = 8000
}

variable "db_host" {
  description = "Hostname of the PostgreSQL instance."
  type        = string
}

variable "db_port" {
  description = "Port of the PostgreSQL instance."
  type        = number
}

variable "db_name" {
  description = "Initial database name for ContextEngine."
  type        = string
}

variable "documents_bucket_name" {
  description = "Name of the private S3 bucket for source documents."
  type        = string
}

variable "documents_bucket_arn" {
  description = "ARN of the private S3 bucket for source documents."
  type        = string
}

variable "wiki_bucket_name" {
  description = "Name of the private S3 bucket for wiki markdown backups."
  type        = string
}

variable "wiki_bucket_arn" {
  description = "ARN of the private S3 bucket for wiki markdown backups."
  type        = string
}

variable "sqs_ingest_queue_url" {
  description = "URL of the ingestion SQS queue."
  type        = string
}

variable "sqs_ingest_queue_arn" {
  description = "ARN of the ingestion SQS queue."
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for sessions and query logs."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for sessions and query logs."
  type        = string
}

variable "cognito_user_pool_id" {
  description = "ID of the Cognito user pool."
  type        = string
}

variable "cognito_client_id" {
  description = "ID of the Cognito SPA app client."
  type        = string
}

variable "rds_master_secret_arn" {
  description = "Secrets Manager ARN for the RDS-managed master credentials."
  type        = string
}

variable "openai_secret_arn" {
  description = "Secrets Manager ARN containing OPENAI_API_KEY."
  type        = string
}

variable "ecs_execution_role_name" {
  description = "Existing IAM role name used by ECS to pull images and write logs."
  type        = string
  default     = "context-engine-ecs-execution-role"
}

variable "ecs_task_role_name" {
  description = "Existing IAM role name assumed by the backend application task."
  type        = string
  default     = "context-engine-ecs-task-role"
}
