resource "aws_ecs_task_definition" "api" {
  container_definitions = jsonencode([
    {
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "DATABASE_HOST"
          value = var.db_host
        },
        {
          name  = "DATABASE_NAME"
          value = var.db_name
        },
        {
          name  = "DATABASE_PORT"
          value = tostring(var.db_port)
        },
        {
          name  = "COGNITO_CLIENT_ID"
          value = var.cognito_client_id
        },
        {
          name  = "COGNITO_REGION"
          value = var.aws_region
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = var.cognito_user_pool_id
        },
        {
          name  = "DYNAMODB_TABLE_NAME"
          value = var.dynamodb_table_name
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "RDS_MASTER_SECRET_ARN"
          value = var.rds_master_secret_arn
        },
        {
          name  = "S3_DOCUMENTS_BUCKET"
          value = var.documents_bucket_name
        },
        {
          name  = "S3_WIKI_BUCKET"
          value = var.wiki_bucket_name
        },
        {
          name  = "SQS_INGEST_QUEUE_URL"
          value = var.sqs_ingest_queue_url
        }
      ]
      essential = true
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = local.log_group_name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
      name = local.container_name
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = var.openai_secret_arn
        }
      ]
    }
  ])
  cpu                      = "256"
  execution_role_arn       = data.aws_iam_role.execution.arn
  family                   = "${local.name_prefix}-api"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  task_role_arn            = data.aws_iam_role.task.arn

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-api-task"
  })
}
