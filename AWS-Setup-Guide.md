# AWS Setup Guide for inf4RAG Project

## Overview
This guide will help you set up AWS CLI and configure access to our EKS cluster for the inf4RAG project.

## Prerequisites
- macOS (with Homebrew installed)
- AWS IAM user account (provided by project admin)
- AWS Access Key ID and Secret Access Key (provided by project admin)

## Step 1: Install AWS CLI

```bash
# Install AWS CLI using Homebrew
brew install awscli

# Verify installation
aws --version
```

Expected output: `aws-cli/2.x.x Python/3.x.x Darwin/24.6.0 source/arm64`

## Step 2: Configure AWS Credentials

```bash
# Configure AWS credentials
aws configure
```

When prompted, enter the following information:
- **AWS Access Key ID**: `[Your Access Key ID]` (provided by admin)
- **AWS Secret Access Key**: `[Your Secret Access Key]` (provided by admin)
- **Default region name**: `us-west-2`
- **Default output format**: `json`

## Step 3: Install kubectl and eksctl

```bash
# Install kubectl
brew install kubectl

# Install eksctl for EKS cluster management
brew install eksctl

# Verify installation
kubectl version --client
eksctl version
```

## Step 4: Verify AWS Configuration

```bash
# Test AWS connection
aws sts get-caller-identity
```

Expected output should show your user information:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "448515985423",
    "Arn": "arn:aws:iam::448515985423:user/inf4RAG-[your-username]"
}
```

## Step 5: Connect to EKS Cluster

```bash
# Update kubeconfig to access our EKS cluster
aws eks update-kubeconfig --region us-west-2 --name inf4rag

# Verify cluster access
kubectl get nodes
```

Expected output: You should see 2 t3.micro nodes in Ready status

## Step 6: Verify Cluster Status

```bash
# Check all cluster components
kubectl get all --all-namespaces

# View cluster information
kubectl cluster-info

# Check node details
kubectl describe nodes
```


=================================================================================
from here not ok

## Step 7: Deploy Test Application (Optional)

```bash
# Deploy nginx test
kubectl create deployment nginx --image=nginx

# Expose as LoadBalancer
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Check service status
kubectl get services

# Clean up test deployment
kubectl delete service nginx
kubectl delete deployment nginx
```

## Current Cluster Configuration

- **Cluster Name**: `inf4rag`
- **Region**: `us-west-2`
- **Kubernetes Version**: `v1.32`
- **Node Type**: `t3.micro` (Free Tier)
- **Number of Nodes**: 2
- **Node Group**: `workers`

## Troubleshooting

### Common Issues:

1. **Permission Denied Errors**
   - Ensure your IAM user is in the `inf4RAG` user group
   - Contact admin to verify user group permissions

2. **Region Mismatch**
   - Always use `us-west-2` region in commands
   - Verify with: `aws configure get region`

3. **Cluster Not Found**
   - Ensure you're using the correct cluster name: `inf4rag`
   - Check: `aws eks list-clusters --region us-west-2`

4. **kubectl Connection Issues**
   - Re-run: `aws eks update-kubeconfig --region us-west-2 --name inf4rag`
   - Check context: `kubectl config current-context`

5. **Unable to connect to server**
   - Wait a few minutes for the cluster to be fully ready
   - Verify your AWS credentials are correct

## Security Best Practices

⚠️ **Important Security Notes:**
- Never commit AWS credentials to version control
- Keep your access keys secure and private
- Rotate access keys regularly
- Do not share your credentials with others

## GPU Node Group (Advanced - Optional)

⚠️ **Note**: GPU instances are NOT covered by Free Tier and will incur charges!

If you need GPU support for large LLM models:

```bash
# Create GPU node group (g4dn.xlarge)
eksctl create nodegroup \
  --cluster=inf4rag \
  --region=us-west-2 \
  --name=gpu-nodes \
  --node-type=g4dn.xlarge \
  --nodes=1 \
  --nodes-min=0 \
  --nodes-max=2 \
  --managed

# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/deployments/static/nvidia-device-plugin.yml
```

## Next Steps

Once setup is complete, you can:
1. Deploy inf4RAG project applications
2. Monitor cluster resources with `kubectl top nodes`
3. View application logs with `kubectl logs`
4. Collaborate with team members on deployments

## Useful Commands

```bash
# View all resources
kubectl get all --all-namespaces

# View pods in default namespace
kubectl get pods

# View services
kubectl get services

# View cluster nodes
kubectl get nodes

# Describe a specific pod
kubectl describe pod <pod-name>

# View pod logs
kubectl logs <pod-name>

# Delete a resource
kubectl delete <resource-type> <resource-name>
```

## Support

If you encounter any issues:
1. Check this troubleshooting guide
2. Contact the project admin
3. Refer to AWS documentation: https://docs.aws.amazon.com/eks/

---
**Project**: inf4RAG - Optimizing Cloud-Based Inference for RAG and Agentic Workloads  
**Region**: us-west-2  
**Cluster**: inf4rag  
**Instance Type**: t3.micro (Free Tier)  
**Setup Date**: September 30, 2025
