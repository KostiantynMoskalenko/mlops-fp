variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_profile" {
  type    = string
  default = "kosmos"
}

variable "cluster_name" {
  type    = string
  default = "aiops-quality-cluster"
}

variable "node_instance_type" {
  type    = string
  default = "t3.small"
}

variable "desired_size" {
  type    = number
  default = 2
}

variable "min_size" {
  type    = number
  default = 1
}

variable "max_size" {
  type    = number
  default = 3
}
