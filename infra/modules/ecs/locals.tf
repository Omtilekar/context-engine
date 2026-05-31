locals {
  container_name = "context-engine-api"
  log_group_name = "/ecs/${var.project_name}-${var.environment}"
  name_prefix    = "${var.project_name}-${var.environment}"
}

