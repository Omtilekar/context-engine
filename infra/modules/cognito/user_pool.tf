resource "aws_cognito_user_pool" "main" {
  auto_verified_attributes = ["email"]
  name                     = "${local.name_prefix}-users"
  username_attributes      = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-users"
  })
}

