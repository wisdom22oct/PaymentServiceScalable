#!/bin/bash

# Deploy Payment Service to Kubernetes

echo "Deploying Payment Service to Kubernetes..."

# Check if Minikube is running
if ! minikube status &> /dev/null; then
    echo "✗ Minikube is not running. Start it with: minikube start"
    exit 1
fi

# Set Docker environment to use Minikube's Docker daemon
eval $(minikube docker-env)

# Build Docker image in Minikube
echo "Building Docker image in Minikube..."
docker build -t payment-service:latest .

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."

# Create namespace if needed
# kubectl create namespace ticketing --dry-run=client -o yaml | kubectl apply -f -

# Apply in order: ConfigMap, PVC, MongoDB, Service
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/mongodb-deployment.yaml
kubectl apply -f k8s/mongodb-service.yaml

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
kubectl wait --for=condition=ready pod -l app=payment-mongodb --timeout=120s

# Deploy the Payment Service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Wait for deployment to be ready
echo "Waiting for Payment Service to be ready..."
kubectl wait --for=condition=available deployment/payment-service --timeout=120s

echo ""
echo "✓ Deployment complete!"
echo ""
echo "Check status with:"
echo "  kubectl get pods -l app=payment-service"
echo "  kubectl get svc payment-service"
echo ""
echo "Access the service:"
echo "  minikube service payment-service --url"
echo ""
echo "View logs:"
echo "  kubectl logs -f deployment/payment-service"