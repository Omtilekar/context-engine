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
  cognito_client_id     = module.cognito.user_pool_client_id
  cognito_user_pool_id  = module.cognito.user_pool_id
  documents_bucket_arn  = module.s3.documents_bucket_arn
  documents_bucket_name = module.s3.documents_bucket_name
  dynamodb_table_arn    = aws_dynamodb_table.sessions.arn
  dynamodb_table_name   = aws_dynamodb_table.sessions.name
  db_host               = module.rds.db_address
  db_name               = module.rds.db_name
  db_port               = module.rds.db_port
  desired_count         = var.ecs_desired_count
  ecs_security_group_id = module.vpc.ecs_security_group_id
  environment           = var.environment
  openai_secret_arn     = aws_secretsmanager_secret.openai_api_key.arn
  private_subnet_ids    = module.vpc.private_subnet_ids
  project_name          = var.project_name
  public_subnet_ids     = module.vpc.public_subnet_ids
  rds_master_secret_arn = module.rds.master_secret_arn
  sqs_ingest_queue_arn  = aws_sqs_queue.ingest.arn
  sqs_ingest_queue_url  = aws_sqs_queue.ingest.url
  vpc_id                = module.vpc.vpc_id
  wiki_bucket_arn       = module.s3.wiki_bucket_arn
  wiki_bucket_name      = module.s3.wiki_bucket_name
}

module "s3" {
  source = "./modules/s3"

  account_id   = var.account_id
  common_tags  = local.common_tags
  environment  = var.environment
  project_name = var.project_name
}

module "cloudfront" {
  source = "./modules/cloudfront"

  common_tags                          = local.common_tags
  environment                          = var.environment
  frontend_bucket_arn                  = module.s3.frontend_bucket_arn
  frontend_bucket_name                 = module.s3.frontend_bucket_name
  frontend_bucket_regional_domain_name = module.s3.frontend_bucket_regional_domain_name
  project_name                         = var.project_name
}

module "cognito" {
  source = "./modules/cognito"

  common_tags  = local.common_tags
  environment  = var.environment
  project_name = var.project_name
}

module "cloudwatch" {
  source = "./modules/cloudwatch"

  common_tags    = local.common_tags
  environment    = var.environment
  log_group_name = module.ecs.log_group_name
  project_name   = var.project_name
}
