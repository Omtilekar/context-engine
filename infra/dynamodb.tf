resource "aws_dynamodb_table" "sessions" {
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  name         = "${var.project_name}-${var.environment}-sessions"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-sessions"
  })
}

