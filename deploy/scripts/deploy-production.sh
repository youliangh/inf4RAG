#!/bin/bash
echo "🚀 Deploying to production AWS environment..."

# 应用配置
kubectl apply -k deploy/kubernetes/overlays/production/

# 验证部署
kubectl get all -n vllm-inference

echo "✅ Production deployment complete!"
