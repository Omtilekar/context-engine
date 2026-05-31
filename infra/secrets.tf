resource "aws_secretsmanager_secret" "openai_api_key" {
  description             = "OpenAI API key for ContextEngine runtime calls."
  name                    = "${var.project_name}-${var.environment}-openai-api-key"
  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-openai-api-key"
  })
}

