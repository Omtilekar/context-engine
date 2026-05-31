resource "aws_ecs_service" "api" {
  cluster         = aws_ecs_cluster.main.id
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  name            = "${local.name_prefix}-api"
  task_definition = aws_ecs_task_definition.api.arn

  load_balancer {
    container_name   = local.container_name
    container_port   = var.container_port
    target_group_arn = aws_lb_target_group.api.arn
  }

  network_configuration {
    assign_public_ip = false
    security_groups  = [var.ecs_security_group_id]
    subnets          = var.private_subnet_ids
  }

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-api"
  })

  depends_on = [aws_lb_listener.http]
}

