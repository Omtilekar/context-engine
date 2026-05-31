resource "aws_subnet" "public" {
  for_each = local.public_subnets

  availability_zone       = each.value.availability_zone
  cidr_block              = each.value.cidr_block
  map_public_ip_on_launch = true
  vpc_id                  = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = each.value.name
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  for_each = local.private_subnets

  availability_zone       = each.value.availability_zone
  cidr_block              = each.value.cidr_block
  map_public_ip_on_launch = false
  vpc_id                  = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = each.value.name
    Tier = "private"
  })
}

