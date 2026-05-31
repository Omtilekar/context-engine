output "db_endpoint" {
  description = "Endpoint for the ContextEngine PostgreSQL instance."
  value       = aws_db_instance.main.endpoint
}

output "db_address" {
  description = "Hostname for the ContextEngine PostgreSQL instance."
  value       = aws_db_instance.main.address
}

output "db_instance_id" {
  description = "Identifier of the ContextEngine PostgreSQL instance."
  value       = aws_db_instance.main.identifier
}

output "db_name" {
  description = "Initial database name for ContextEngine."
  value       = aws_db_instance.main.db_name
}

output "db_port" {
  description = "Port exposed by the ContextEngine PostgreSQL instance."
  value       = aws_db_instance.main.port
}

output "master_secret_arn" {
  description = "Secrets Manager ARN for the RDS-managed master credentials."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
  sensitive   = true
}

output "subnet_group_name" {
  description = "Name of the RDS subnet group."
  value       = aws_db_subnet_group.main.name
}
