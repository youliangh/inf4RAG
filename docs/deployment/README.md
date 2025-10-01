# vLLM Deployment Guide

## Prerequisites
- Kubernetes cluster (minikube, EKS, etc.)
- kubectl configured
- Docker images available

## Local Development
```bash
# Deploy to local minikube
kubectl apply -k deploy/kubernetes/overlays/local/

# Check status
kubectl get all -n vllm-inference

# Port forward for testing
kubectl port-forward svc/vllm-service 8000:8000 -n vllm-inference
```

## Production Deployment (AWS)
```bash
# Deploy to AWS EKS
kubectl apply -k deploy/kubernetes/overlays/production/

# Check status
kubectl get all -n vllm-inference
```

## Health Checks
```bash
# Run health check script
./tests/health/health-check.sh
```
