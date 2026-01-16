variable "aws_region" {
  description = "AWS region for the ECR repository"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile name"
  type        = string
  default     = "kosmos"
}

variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "inference-api"
}

variable "scan_on_push" {
  description = "Enable vulnerability scanning on image push"
  type        = bool
  default     = true
}

variable "image_tag_mutability" {
  description = "Should image tags be mutable or immutable"
  type        = string
  default     = "MUTABLE"
}
