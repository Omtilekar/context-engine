locals {
  bucket_names = {
    documents = "${var.project_name}-${var.environment}-documents-${var.account_id}"
    frontend  = "${var.project_name}-${var.environment}-frontend-${var.account_id}"
    wiki      = "${var.project_name}-${var.environment}-wiki-${var.account_id}"
  }
}

