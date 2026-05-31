resource "aws_s3_bucket" "main" {
  for_each = local.bucket_names

  bucket = each.value

  tags = merge(var.common_tags, {
    Name    = each.value
    Purpose = each.key
  })
}

