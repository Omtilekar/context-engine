output "user_pool_arn" {
  description = "ARN of the Cognito user pool."
  value       = aws_cognito_user_pool.main.arn
}

output "user_pool_client_id" {
  description = "ID of the Cognito SPA app client."
  value       = aws_cognito_user_pool_client.spa.id
}

output "user_pool_id" {
  description = "ID of the Cognito user pool."
  value       = aws_cognito_user_pool.main.id
}

