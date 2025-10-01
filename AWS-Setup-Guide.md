# AWS Setup Guide for inf4RAG Project

## Overview
This guide will help you set up AWS CLI and configure access to our EKS cluster for the inf4RAG project. The GPT-2 inference service is already deployed and ready to use.

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

Expected output: You should see 3 nodes (2 t3.micro + 1 t3.large) in Ready status

## Step 6: Access the GPT-2 Service

The GPT-2 inference service is already deployed and running. You can access it in two ways:

### Option 1: Using LoadBalancer (External Access)

```bash
# Get the external URL
kubectl get service gpt2-simple-service -n vllm-inference

# Test the service (replace with actual LoadBalancer URL)
curl http://a971802cc82fb4bc28974a5beab4291d-1506849826.us-west-2.elb.amazonaws.com:8000/health
```

### Option 2: Using Port Forward (Recommended for Development)

```bash
# Port forward to local machine
kubectl port-forward service/gpt2-simple-service 8000:8000 -n vllm-inference

# In another terminal, test the service
curl http://localhost:8000/health
```

## Step 7: Test the GPT-2 API

Once connected, you can test the GPT-2 service:

```bash
# Health check
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models

# Generate text
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt2",
    "prompt": "Hello, world!",
    "max_tokens": 50
  }'
```

## Current Cluster Configuration

- **Cluster Name**: `inf4rag`
- **Region**: `us-west-2`
- **Kubernetes Version**: `v1.32`
- **Node Types**: 
  - 2x `t3.micro` (Free Tier)
  - 1x `t3.large` (GPT-2 service)
- **Deployed Services**:
  - GPT-2 Inference Service (namespace: `vllm-inference`)

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

5. **Service Not Accessible**
   - Check if port-forward is running: `kubectl port-forward service/gpt2-simple-service 8000:8000 -n vllm-inference`
   - Verify service status: `kubectl get pods -n vllm-inference`

## Security Best Practices

⚠️ **Important Security Notes:**
- Never commit AWS credentials to version control
- Keep your access keys secure and private
- Rotate access keys regularly
- Do not share your credentials with others

## Useful Commands

```bash
# View all resources
kubectl get all --all-namespaces

# View GPT-2 service pods
kubectl get pods -n vllm-inference

# View GPT-2 service
kubectl get service -n vllm-inference

# View cluster nodes
kubectl get nodes

# Port forward to GPT-2 service
kubectl port-forward service/gpt2-simple-service 8000:8000 -n vllm-inference

# View GPT-2 service logs
kubectl logs -n vllm-inference -l app=gpt2-simple

# Test GPT-2 API
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt2", "prompt": "Your prompt here", "max_tokens": 50}'
```

## Next Steps

Once setup is complete, you can:
1. Use the GPT-2 service for text generation
2. Integrate with your RAG applications
3. Monitor service performance
4. Wait for GPU quota approval for larger models

## Support

If you encounter any issues:
1. Check this troubleshooting guide
2. Contact the project admin
3. Refer to AWS documentation: https://docs.aws.amazon.com/eks/

---
**Project**: inf4RAG - Optimizing Cloud-Based Inference for RAG and Agentic Workloads  
**Region**: us-west-2  
**Cluster**: inf4rag  
**Instance Types**: t3.micro (Free Tier) + t3.large (GPT-2)  
**Deployed Services**: GPT-2 Inference API  
**Setup Date**: October 1, 2025