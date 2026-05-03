#!/bin/bash

# Build Docker image for Payment Service

echo "Building Payment Service Docker image..."

# Build the image
docker build -t payment-service:latest .

if [ $? -eq 0 ]; then
    echo "√ Docker image built successfully"
    echo "Image: payment-service:latest"
else
    echo "X Docker build failed"
    exit 1
fi

# Show image details
echo ""
echo "Image details:"
docker images payment-service:latest