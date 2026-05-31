resource "aws_s3_bucket_lifecycle_configuration" "main" {
  for_each = aws_s3_bucket.main

  bucket = each.value.id

  rule {
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"
  }
}

