locals {
  name_prefix = "${var.project_name}-${var.environment}"

  public_subnets = {
    for index, cidr in var.public_subnet_cidrs :
    tostring(index) => {
      availability_zone = var.availability_zones[index]
      cidr_block        = cidr
      name              = "${local.name_prefix}-public-${index + 1}"
    }
  }

  private_subnets = {
    for index, cidr in var.private_subnet_cidrs :
    tostring(index) => {
      availability_zone = var.availability_zones[index]
      cidr_block        = cidr
      name              = "${local.name_prefix}-private-${index + 1}"
    }
  }
}

