# Agentic-LLM-Powered-Food-Rescue-Network

## Run on Kubernetes (kind)

1) Create a local cluster:
```bash
kind create cluster
```

2) Build images:
```bash
docker build -t foodrescue-backend:local .
docker build -t foodrescue-frontend:local --build-arg REACT_APP_API_BASE_URL=http://foodrescue-backend:8000 ./frontend
```

3) Load images into kind:
```bash
kind load docker-image foodrescue-backend:local
kind load docker-image foodrescue-frontend:local
```

4) Set your ORS key and apply manifests:
```bash
# Edit k8s/backend-secret.yaml and replace ORS_API_KEY
kubectl apply -f k8s/
```

5) Check status:
```bash
kubectl get pods
kubectl get svc
```

6) Port-forward the frontend:
```bash
kubectl port-forward svc/foodrescue-frontend 3000:3000
```

Then open http://localhost:3000 in your browser.
