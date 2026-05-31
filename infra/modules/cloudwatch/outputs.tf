output "log_group_arn" {
  description = "ARN of the ECS application log group."
  value       = aws_cloudwatch_log_group.ecs.arn
}

output "log_group_name" {
  description = "Name of the ECS application log group."
  value       = aws_cloudwatch_log_group.ecs.name
}

