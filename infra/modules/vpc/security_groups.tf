resource "aws_security_group" "alb" {
  description = "Allow public HTTP and HTTPS traffic to the ContextEngine ALB."
  name        = "${local.name_prefix}-alb-sg"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-alb-sg"
  })
}

resource "aws_security_group" "ecs" {
  description = "Allow only ALB traffic to ContextEngine ECS tasks."
  name        = "${local.name_prefix}-ecs-sg"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-ecs-sg"
  })
}

resource "aws_security_group" "rds" {
  description = "Allow only ECS traffic to ContextEngine RDS PostgreSQL."
  name        = "${local.name_prefix}-rds-sg"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rds-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Allow public HTTP traffic."
  from_port         = 80
  ip_protocol       = "tcp"
  security_group_id = aws_security_group.alb.id
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Allow public HTTPS traffic."
  from_port         = 443
  ip_protocol       = "tcp"
  security_group_id = aws_security_group.alb.id
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Allow ALB outbound traffic to ECS tasks."
  ip_protocol       = "-1"
  security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_ingress_rule" "ecs_api" {
  description                  = "Allow API traffic from the ALB."
  from_port                    = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id
  security_group_id            = aws_security_group.ecs.id
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Allow ECS outbound traffic for AWS APIs and package endpoints."
  ip_protocol       = "-1"
  security_group_id = aws_security_group.ecs.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_postgres" {
  description                  = "Allow PostgreSQL traffic from ECS tasks."
  from_port                    = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id
  security_group_id            = aws_security_group.rds.id
  to_port                      = 5432
}

