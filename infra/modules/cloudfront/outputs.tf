output "distribution_arn" {
  description = "ARN of the frontend CloudFront distribution."
  value       = aws_cloudfront_distribution.frontend.arn
}

output "distribution_domain_name" {
  description = "Domain name of the frontend CloudFront distribution."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "distribution_id" {
  description = "ID of the frontend CloudFront distribution."
  value       = aws_cloudfront_distribution.frontend.id
}

output "origin_access_control_id" {
  description = "ID of the CloudFront origin access control."
  value       = aws_cloudfront_origin_access_control.frontend.id
}

