output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.this.repository_url
}

output "repository_arn" {
  description = "The ARN of the ECR repository"
  value       = aws_ecr_repository.this.arn
}
