resource "aws_s3_bucket_public_access_block" "main" {
  for_each = aws_s3_bucket.main

  block_public_acls       = true
  block_public_policy     = true
  bucket                  = each.value.id
  ignore_public_acls      = true
  restrict_public_buckets = true
}

