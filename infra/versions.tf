terraform {
  required_version = ">= 1.15.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "context-engine-tf-state-256716302630"
    key            = "prod/terraform.tfstate"
    profile        = "context-engine-admin"
    region         = "us-east-1"
    dynamodb_table = "context-engine-tf-lock"
    encrypt        = true
  }
}
