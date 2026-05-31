output "common_tags" {
  description = "Common tags applied to AWS resources by the root provider."
  value       = local.common_tags
}

output "resource_name_prefix" {
  description = "Prefix used for ContextEngine AWS resource names."
  value       = "${var.project_name}-${var.environment}"
}

output "vpc_id" {
  description = "ID of the ContextEngine VPC."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for ALB and NAT resources."
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs for ECS and RDS resources."
  value       = module.vpc.private_subnet_ids
}

output "alb_security_group_id" {
  description = "Security group ID for the public ALB."
  value       = module.vpc.alb_security_group_id
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS tasks."
  value       = module.vpc.ecs_security_group_id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS PostgreSQL."
  value       = module.vpc.rds_security_group_id
}

output "rds_endpoint" {
  description = "Connection endpoint for the ContextEngine PostgreSQL instance."
  value       = module.rds.db_endpoint
}

output "rds_instance_id" {
  description = "Identifier of the ContextEngine PostgreSQL instance."
  value       = module.rds.db_instance_id
}

output "rds_master_secret_arn" {
  description = "Secrets Manager ARN for the RDS-managed master credentials."
  value       = module.rds.master_secret_arn
  sensitive   = true
}

output "alb_dns_name" {
  description = "DNS name of the public application load balancer."
  value       = module.ecs.alb_dns_name
}

output "backend_ecr_repository_url" {
  description = "ECR repository URL for the backend container image."
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ContextEngine ECS cluster."
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ContextEngine ECS service."
  value       = module.ecs.service_name
}

output "documents_bucket_name" {
  description = "Name of the private S3 bucket for source documents."
  value       = module.s3.documents_bucket_name
}

output "frontend_bucket_name" {
  description = "Name of the private S3 bucket for frontend build artifacts."
  value       = module.s3.frontend_bucket_name
}

output "wiki_bucket_name" {
  description = "Name of the private S3 bucket for wiki markdown backups."
  value       = module.s3.wiki_bucket_name
}

output "cloudfront_distribution_domain_name" {
  description = "CloudFront domain name serving the frontend SPA."
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for frontend deployments and invalidations."
  value       = module.cloudfront.distribution_id
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito user pool for ContextEngine users."
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito SPA app client."
  value       = module.cognito.user_pool_client_id
}

output "dynamodb_sessions_table_name" {
  description = "Name of the DynamoDB table for sessions and query logs."
  value       = aws_dynamodb_table.sessions.name
}

output "sqs_ingest_queue_url" {
  description = "URL of the ingestion SQS queue."
  value       = aws_sqs_queue.ingest.url
}

output "sqs_ingest_dlq_url" {
  description = "URL of the ingestion dead-letter SQS queue."
  value       = aws_sqs_queue.ingest_dlq.url
}

output "openai_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret reserved for OPENAI_API_KEY."
  value       = aws_secretsmanager_secret.openai_api_key.arn
  sensitive   = true
}

output "ecs_log_group_name" {
  description = "CloudWatch log group name used by ECS task logs."
  value       = module.cloudwatch.log_group_name
}
