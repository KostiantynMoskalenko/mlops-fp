# CI/CD full process: from push to redeploy in EKS
# Preconditions: already deployed ECR, EKS and VPC
## Algorithm

```
GitLab Repo → GitLab CI/CD → AWS ECR → ArgoCD → EKS Cluster
```

## Step-by-stem process

### 1. Developer pushes changes in GitLab

```bash
git add .
git commit -m "Update model or code"
git push origin main
```

**Possible changes:**
- Application code (`predict.py`, `requirements.txt`)
- Dockerfile
- Helm chart (`helm/` folder)
- ArgoCD configuration (`argocd/application.yaml`)

### 2. GitLab CI/CD finds changes

- GitLab find automaticaly push in branch: `main`, `master`, or `develop`
- Pipeline runs according with `.gitlab-ci.yml`

### 3. Build Stage - Docker image assemly

**Job: `build`**

**Deployment steps:**

1. **Environment inicialization:**
   - Docker-in-Docker (dind) service is startig
   - AWS CLI is installing

2. **Authorization in в AWS ECR:**
   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin $ECR_REGISTRY
   ```
   - Authorisation tokens for ECR receiving 
   - Docker login starts

3. **Docker image assemling:**
   ```bash
   docker build -t $IMAGE_TAG .
   ```
   - Image created with following teg: `fast-api-service:24ffgh24` (commit SHA)
   - Dockerfile running:
     - Basic image: `python:3.11-slim`
     - `requirements.txt` and `predict.py`copying
     - Dependencies created (FastAPI, uvicorn)

4. **Tagging and publicing in ECR:**
   ```bash
   docker tag $IMAGE_TAG $ECR_REGISTRY/$IMAGE_TAG
   docker push $ECR_REGISTRY/$IMAGE_TAG
   docker tag $IMAGE_TAG $ECR_REGISTRY/$CI_REGISTRY_IMAGE:latest
   docker push $ECR_REGISTRY/$CI_REGISTRY_IMAGE:latest
   ```
   - The image pushes with two tags:
     - `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:24ffgh24` (commit SHA)
     - `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:latest` (latest)

**The result:** Docker image is accessible in AWS ECR

### 4. ArgoCD tracking changes in Git repository 

**How does ArgoCD work:**

1. **ArgoCD Application tuned:**
   - It tracks repository: `https://gitlab.com/eadors/mlops-fp.git`
   - Branch: `main`
   - Path: `helm/` (Helm chart)
   - Auto-sync switched on with checking interval (default 3 minutes)

2. **ArgoCD discovers changes:**
   - ArgoCD tracks Git repository
   - If there is changes in `helm/`folder or in `argocd/application.yaml`:
     - ArgoCD finds new commit
     - It compares current cluster stage with necessary Git stage

3. **Auto-sync policy:**
   - `prune: true` - removes resources which are absence in Git
   - `selfHeal: true` - if someone change the stage it restore correct stage automaticaly
   - `allowEmpty: false` - doesn't allow empty sync

### 5. ArgoCD synchronises  changes with EKS cluster

**Synchronisation process:**

1. **ArgoCD reads Helm chart:**
   - Download `helm/Chart.yaml`
   - Download `helm/values.yaml`
   - Applies parameters from `argocd/application.yaml`:
     ```yaml
     image.repository: 451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service
     image.tag: latest
     ```

2. **Kubernetes manifests generation:**
   - ArgoCD runs `helm template` with parameters
   - Generate Kubernetes resources:
     - Deployment
     - Service
     - ServiceAccount
     - Ingress (if enabled)
     - HPA (if enabled)

3. **Changes apply to cluster:**
   - ArgoCD use Kubernetes API for changes apply
   - `kubectl apply` runs for new/updated resources

### 6. Kubernetes updates Deployment

**Updates process in EKS:**

1. **Deployment Controller finds changes:**
   - Kubernetes finds Deployment new version
   - Compare current stage with necessary

2. **Rolling Update:**
   - Kubernetes creates new Pods with new image
   - New image: `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:latest`
   - Old Pods continue work until new ones are ready

3. **Readiness Probe:**
   - Kubernetes checks `/health` endpoint
   - When new Pods are ready (readiness probe successfully):
     - Trafic switches to the new Pods
     - Old Pods finish

4. **The result:**
   - Service updated to the new version
   - Minimal downtime (rolling update)
   - 2 replics work with the new code

### 7. Status check

**Process monitoring:**

1. **GitLab CI/CD:**
   - Build job status check in GitLab UI
   - Check that the image successfully pushed in ECR

2. **ArgoCD UI:**
   - Open ArgoCD dashboard
   - Check status of application `mlops-inference-service`
   - See synchronization in real time

3. **Kubernetes:**
   ```bash
   kubectl get pods -n default
   kubectl get deployment mlops-inference-service -n default
   kubectl describe deployment mlops-inference-service -n default
   ```

4. **Service testing:**
   ```bash
   kubectl port-forward svc/mlops-inference-service 8000:8000 -n default
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"input": "test"}'
   ```

## Update scenarios

### Scenario 1: App code update

1. `predict.py` or `requirements.txt` changes
2. Push in GitLab → Build job assemble a new image
3. The image has been pushed in ECR with tag `latest`
4. ArgoCD didn't find changes in `helm/`, but image `latest` updated
5. **It is necessary to update Helm chart** or change `image.tag` in ArgoCD application

**Solution:** Update `argocd/application.yaml` with new tag or use commit SHA

### Scenario 2: Helm chart update

1. Changes in `helm/values.yaml` configuration (for example, `replicaCount: 3`)
2. Push в GitLab
3. ArgoCD finds changes in `helm/` folder
4. ArgoCD automatically synchronize the changes
5. Kubernetes extends deployment up to 3 replics

### Scenario 3: Dockerfile update

1. `Dockerfile` is changed
2. Push в GitLab → Build job assemble a new image
3. The image is pushed in ECR
4. ArgoCD use image `latest` and automatically use this image
5. Kubernetes uses rolling update

## Important

### Images' security

- The image with tag `latest` always indicates to the last assembly
- The image with commit SHA allows rollback to the necessary version
- Recommended to use specific tags for production

### Automation 

- ArgoCD auto-sync provides automatically update
- Self-heal restore stage in case of manual changes
- Prune deletes out of date resources

### Monitoring

- ArgoCD UI shows stage of synchronization
- Kubernetes events shows update process
- GitLab CI/CD shows th image stage

## Deployment time

- **Build job:** 2-5 minutes (depends on the image size)
- **ArgoCD sync:** 3-5 minutes (check interval + synchronization time)
- **Kubernetes rolling update:** 1-3 minutes (depends on number of replics)
- **Total time:** 6-13 minutes from push to total redeploy