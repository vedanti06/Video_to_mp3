#!/usr/bin/env bash
# Apply Kubernetes manifests in dependency order (used by Jenkins CD stage).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Deploy: RabbitMQ ==="
kubectl apply -f rabbit/manifests/secret.yaml
kubectl apply -f rabbit/manifests/pvc.yaml
kubectl apply -f rabbit/manifests/statefulset.yaml
kubectl apply -f rabbit/manifests/service.yaml

echo "=== Deploy: MongoDB ==="
kubectl apply -f mongo/manifests/deployment.yaml
kubectl apply -f mongo/manifests/service.yaml

echo "=== Deploy: Auth ==="
kubectl apply -f auth/manifests/configmap.yaml
kubectl apply -f auth/manifests/secret.yaml
kubectl apply -f auth/manifests/auth-deploy.yaml
kubectl apply -f auth/manifests/service.yaml

echo "=== Deploy: Gateway ==="
kubectl apply -f gateway/manifests/configmap.yaml
kubectl apply -f gateway/manifests/secret.yaml
kubectl apply -f gateway/manifests/gateway-deploy.yaml
kubectl apply -f gateway/manifests/service.yaml

echo "=== Deploy: Convertor ==="
kubectl apply -f convertor/manifests/configmap.yaml
kubectl apply -f convertor/manifests/secret.yaml
kubectl apply -f convertor/manifests/convertor-deploy.yaml

echo "=== Pods ==="
kubectl get pods -l 'app in (gateway,auth,convertor,mongo,rabbitmq)'

echo "=== Restart apps to pull new images ==="
kubectl rollout restart deployment/gateway deployment/auth deployment/convertor
