resource "aws_db_instance" "main" {
  allocated_storage                   = var.allocated_storage
  auto_minor_version_upgrade          = true
  backup_retention_period             = var.backup_retention_period
  copy_tags_to_snapshot               = true
  db_name                             = var.db_name
  db_subnet_group_name                = aws_db_subnet_group.main.name
  deletion_protection                 = false
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]
  engine                              = "postgres"
  engine_version                      = "16"
  identifier                          = "${local.name_prefix}-rds"
  instance_class                      = var.db_instance_class
  manage_master_user_password         = true
  max_allocated_storage               = 100
  multi_az                            = false
  performance_insights_enabled        = false
  publicly_accessible                 = false
  skip_final_snapshot                 = true
  storage_encrypted                   = true
  storage_type                        = "gp3"
  username                            = var.db_username
  vpc_security_group_ids              = [var.rds_security_group_id]

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rds"
  })
}

