resource "aws_s3_bucket_ownership_controls" "main" {
  for_each = aws_s3_bucket.main

  bucket = each.value.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

