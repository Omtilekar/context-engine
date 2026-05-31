resource "aws_db_subnet_group" "main" {
  description = "Private subnets for the ContextEngine PostgreSQL instance."
  name        = "${local.name_prefix}-rds-subnet-group"
  subnet_ids  = var.private_subnet_ids

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rds-subnet-group"
  })
}

