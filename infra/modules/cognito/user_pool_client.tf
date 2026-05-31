resource "aws_cognito_user_pool_client" "spa" {
  access_token_validity                = 60
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  auth_session_validity                = 3
  callback_urls                        = ["http://localhost:5173/auth/callback"]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]
  generate_secret                      = false
  id_token_validity                    = 60
  logout_urls                          = ["http://localhost:5173"]
  name                                 = "${local.name_prefix}-frontend"
  prevent_user_existence_errors        = "ENABLED"
  refresh_token_validity               = 7
  supported_identity_providers         = ["COGNITO"]
  user_pool_id                         = aws_cognito_user_pool.main.id

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

