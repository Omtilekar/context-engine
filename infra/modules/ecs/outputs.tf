output "alb_dns_name" {
  description = "DNS name of the application load balancer."
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Route 53 zone ID of the application load balancer."
  value       = aws_lb.main.zone_id
}

output "cluster_name" {
  description = "Name of the ContextEngine ECS cluster."
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "Name of the ContextEngine ECS service."
  value       = aws_ecs_service.api.name
}

output "ecr_repository_url" {
  description = "URL of the backend ECR repository."
  value       = aws_ecr_repository.backend.repository_url
}

output "target_group_arn" {
  description = "ARN of the backend API target group."
  value       = aws_lb_target_group.api.arn
}

output "log_group_name" {
  description = "CloudWatch log group name used by ECS task logs."
  value       = local.log_group_name
}

