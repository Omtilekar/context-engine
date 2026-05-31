locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = local.common_tags
  }
}

module "vpc" {
  source = "./modules/vpc"

  availability_zones   = var.availability_zones
  common_tags          = local.common_tags
  environment          = var.environment
  private_subnet_cidrs = var.private_subnet_cidrs
  project_name         = var.project_name
  public_subnet_cidrs  = var.public_subnet_cidrs
  vpc_cidr             = var.vpc_cidr
}

module "rds" {
  source = "./modules/rds"

  common_tags           = local.common_tags
  environment           = var.environment
  private_subnet_ids    = module.vpc.private_subnet_ids
  project_name          = var.project_name
  rds_security_group_id = module.vpc.rds_security_group_id
}
