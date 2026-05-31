resource "aws_sqs_queue" "ingest_dlq" {
  message_retention_seconds = 1209600
  name                      = "${var.project_name}-${var.environment}-ingest-dlq"
  sqs_managed_sse_enabled   = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-ingest-dlq"
  })
}

resource "aws_sqs_queue" "ingest" {
  message_retention_seconds = 345600
  name                      = "${var.project_name}-${var.environment}-ingest-queue"
  receive_wait_time_seconds = 10
  sqs_managed_sse_enabled   = true
  visibility_timeout_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-ingest-queue"
  })
}

