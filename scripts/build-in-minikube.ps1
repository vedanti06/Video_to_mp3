# Build gateway + convertor into Minikube's Docker (so pods use your local source, not Hub).
# Run from repo root after changing Python code.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
minikube docker-env --shell powershell | Invoke-Expression
Set-Location $Root
docker build -t vd0610/gateway:latest -f gateway/Dockerfile gateway/
docker build -t vd0610/convertor:latest -f convertor/Dockerfile convertor/
kubectl rollout restart deployment/gateway deployment/convertor
# Restore normal Docker (optional): minikube docker-env --shell powershell -u | Invoke-Expression
