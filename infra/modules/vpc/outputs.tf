output "vpc_id" {
  description = "ID of the ContextEngine VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets used by the ALB and NAT gateway."
  value       = [for subnet in aws_subnet.public : subnet.id]
}

output "private_subnet_ids" {
  description = "IDs of private subnets used by ECS and RDS."
  value       = [for subnet in aws_subnet.private : subnet.id]
}

output "alb_security_group_id" {
  description = "Security group ID for the public ALB."
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS tasks."
  value       = aws_security_group.ecs.id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS PostgreSQL."
  value       = aws_security_group.rds.id
}

output "nat_gateway_id" {
  description = "ID of the single NAT gateway used by private subnets."
  value       = aws_nat_gateway.main.id
}

