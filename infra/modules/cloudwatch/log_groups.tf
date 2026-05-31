resource "aws_cloudwatch_log_group" "ecs" {
  name              = var.log_group_name
  retention_in_days = 7

  tags = merge(var.common_tags, {
    Name = var.log_group_name
  })
}

