output "documents_bucket_arn" {
  description = "ARN of the private S3 bucket for source documents."
  value       = aws_s3_bucket.main["documents"].arn
}

output "documents_bucket_name" {
  description = "Name of the private S3 bucket for source documents."
  value       = aws_s3_bucket.main["documents"].bucket
}

output "frontend_bucket_arn" {
  description = "ARN of the private S3 bucket for frontend build artifacts."
  value       = aws_s3_bucket.main["frontend"].arn
}

output "frontend_bucket_name" {
  description = "Name of the private S3 bucket for frontend build artifacts."
  value       = aws_s3_bucket.main["frontend"].bucket
}

output "frontend_bucket_regional_domain_name" {
  description = "Regional domain name of the frontend S3 bucket."
  value       = aws_s3_bucket.main["frontend"].bucket_regional_domain_name
}

output "wiki_bucket_arn" {
  description = "ARN of the private S3 bucket for wiki markdown backups."
  value       = aws_s3_bucket.main["wiki"].arn
}

output "wiki_bucket_name" {
  description = "Name of the private S3 bucket for wiki markdown backups."
  value       = aws_s3_bucket.main["wiki"].bucket
}

