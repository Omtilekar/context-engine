resource "aws_cloudfront_origin_access_control" "frontend" {
  description                       = "OAC for the private ContextEngine frontend bucket."
  name                              = "${local.name_prefix}-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

