module "eks_node_group" {
  source  = "terraform-aws-modules/eks/aws//modules/eks-managed-node-group"
  version = "~> 20.0"

  name         = "default-node-group"
  cluster_name = module.eks.cluster_name
  subnet_ids   = module.vpc.private_subnets

  # IMPORTANT: required by the node group module validation
  cluster_service_cidr = "172.20.0.0/16"

  instance_types = [var.node_instance_type]

  min_size     = var.min_size
  max_size     = var.max_size
  desired_size = var.desired_size
}
