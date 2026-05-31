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
