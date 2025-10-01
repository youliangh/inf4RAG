#!/bin/bash
echo "🔍 Checking vLLM service health..."

# 检查命名空间
echo "📋 Checking namespace..."
kubectl get namespace vllm-inference

# 检查部署
echo "🚀 Checking deployment..."
kubectl get deployment -n vllm-inference

# 检查服务
echo "🌐 Checking services..."
kubectl get svc -n vllm-inference

# 检查Pod状态
echo "📦 Checking pods..."
kubectl get pods -n vllm-inference

echo "✅ Health check complete!"
