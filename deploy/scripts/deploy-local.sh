#!/bin/bash
echo "🚀 Deploying to local minikube environment..."

# 应用配置
kubectl apply -k deploy/kubernetes/overlays/local/

# 验证部署
kubectl get all -n vllm-inference

echo "✅ Local deployment complete!"
