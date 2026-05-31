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

module "ecs" {
  source = "./modules/ecs"

  alb_security_group_id = module.vpc.alb_security_group_id
  aws_region            = var.aws_region
  common_tags           = local.common_tags
  db_host               = module.rds.db_address
  db_name               = module.rds.db_name
  db_port               = module.rds.db_port
  desired_count         = var.ecs_desired_count
  ecs_security_group_id = module.vpc.ecs_security_group_id
  environment           = var.environment
  private_subnet_ids    = module.vpc.private_subnet_ids
  project_name          = var.project_name
  public_subnet_ids     = module.vpc.public_subnet_ids
  rds_master_secret_arn = module.rds.master_secret_arn
  vpc_id                = module.vpc.vpc_id
}

module "s3" {
  source = "./modules/s3"

  account_id   = var.account_id
  common_tags  = local.common_tags
  environment  = var.environment
  project_name = var.project_name
}
