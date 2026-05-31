output "common_tags" {
  description = "Common tags applied to AWS resources by the root provider."
  value       = local.common_tags
}

output "resource_name_prefix" {
  description = "Prefix used for ContextEngine AWS resource names."
  value       = "${var.project_name}-${var.environment}"
}

