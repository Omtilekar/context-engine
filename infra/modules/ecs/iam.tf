data "aws_iam_role" "execution" {
  name = var.ecs_execution_role_name
}

data "aws_iam_role" "task" {
  name = var.ecs_task_role_name
}

data "aws_iam_policy_document" "execution_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.openai_secret_arn]
  }
}

data "aws_iam_policy_document" "task_runtime" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.rds_master_secret_arn]
  }

  statement {
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "${var.documents_bucket_arn}/*",
      "${var.wiki_bucket_arn}/*",
    ]
  }

  statement {
    actions   = ["s3:ListBucket"]
    resources = [var.documents_bucket_arn, var.wiki_bucket_arn]
  }

  statement {
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ReceiveMessage",
      "sqs:SendMessage",
    ]
    resources = [var.sqs_ingest_queue_arn]
  }

  statement {
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
    ]
    resources = [var.dynamodb_table_arn]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "${local.name_prefix}-ecs-execution-secrets"
  policy = data.aws_iam_policy_document.execution_secrets.json
  role   = data.aws_iam_role.execution.id
}

resource "aws_iam_role_policy" "task_runtime" {
  name   = "${local.name_prefix}-ecs-task-runtime"
  policy = data.aws_iam_policy_document.task_runtime.json
  role   = data.aws_iam_role.task.id
}
