data "aws_iam_role" "execution" {
  name = var.ecs_execution_role_name
}

data "aws_iam_role" "task" {
  name = var.ecs_task_role_name
}

