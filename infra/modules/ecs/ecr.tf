resource "aws_ecr_repository" "backend" {
  force_delete         = true
  image_tag_mutability = "MUTABLE"
  name                 = "context-engine-backend"

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.common_tags, {
    Name = "context-engine-backend"
  })
}

resource "aws_ecr_lifecycle_policy" "backend" {
  policy = jsonencode({
    rules = [
      {
        action = {
          type = "expire"
        }
        description  = "Keep the latest 5 backend images."
        rulePriority = 1
        selection = {
          countNumber = 5
          countType   = "imageCountMoreThan"
          tagStatus   = "any"
        }
      }
    ]
  })
  repository = aws_ecr_repository.backend.name
}

