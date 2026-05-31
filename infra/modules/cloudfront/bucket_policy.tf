data "aws_iam_policy_document" "frontend_bucket" {
  statement {
    actions = ["s3:GetObject"]

    condition {
      test     = "StringEquals"
      values   = [aws_cloudfront_distribution.frontend.arn]
      variable = "AWS:SourceArn"
    }

    principals {
      identifiers = ["cloudfront.amazonaws.com"]
      type        = "Service"
    }

    resources = ["${var.frontend_bucket_arn}/*"]
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = var.frontend_bucket_name
  policy = data.aws_iam_policy_document.frontend_bucket.json
}

