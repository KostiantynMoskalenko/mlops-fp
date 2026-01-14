# Повний процес CI/CD: від пушу до редеплою в EKS

## Архітектура

```
GitLab Repo → GitLab CI/CD → AWS ECR → ArgoCD → EKS Cluster
```

## Детальний процес

### 1. Розробник пушить зміни в GitLab

```bash
git add .
git commit -m "Update model or code"
git push origin main
```

**Що може змінитись:**
- Код додатку (`predict.py`, `requirements.txt`)
- Dockerfile
- Helm чарт (`helm/` директорія)
- ArgoCD конфігурація (`argocd/application.yaml`)

### 2. GitLab CI/CD виявляє зміни

- GitLab автоматично виявляє push в гілки: `main`, `master`, або `develop`
- Запускається pipeline згідно з `.gitlab-ci.yml`

### 3. Build Stage - Збірка Docker образу

**Job: `build`**

**Кроки виконання:**

1. **Ініціалізація середовища:**
   - Запускається Docker-in-Docker (dind) сервіс
   - Встановлюється AWS CLI

2. **Авторизація в AWS ECR:**
   ```bash
   aws ecr get-login-password --region eu-central-1 | \
     docker login --username AWS --password-stdin $ECR_REGISTRY
   ```
   - Отримується токен авторизації для ECR
   - Виконується Docker login

3. **Збірка Docker образу:**
   ```bash
   docker build -t $IMAGE_TAG .
   ```
   - Створюється образ з тегом: `fast-api-service:24ffgh24` (commit SHA)
   - Виконується Dockerfile:
     - Базовий образ: `python:3.11-slim`
     - Копіюються `requirements.txt` та `predict.py`
     - Встановлюються залежності (FastAPI, uvicorn)

4. **Тегування та публікація в ECR:**
   ```bash
   docker tag $IMAGE_TAG $ECR_REGISTRY/$IMAGE_TAG
   docker push $ECR_REGISTRY/$IMAGE_TAG
   docker tag $IMAGE_TAG $ECR_REGISTRY/$CI_REGISTRY_IMAGE:latest
   docker push $ECR_REGISTRY/$CI_REGISTRY_IMAGE:latest
   ```
   - Образ пушиться з двома тегами:
     - `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:24ffgh24` (commit SHA)
     - `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:latest` (latest)

**Результат:** Docker образ доступний в AWS ECR

### 4. ArgoCD відстежує зміни в Git репозиторії

**Як працює ArgoCD:**

1. **ArgoCD Application налаштований:**
   - Відстежує репозиторій: `https://gitlab.com/your-username/your-repo.git`
   - Гілка: `main`
   - Шлях: `helm/` (Helm чарт)
   - Auto-sync увімкнено з інтервалом перевірки (зазвичай 3 хвилини)

2. **ArgoCD виявляє зміни:**
   - ArgoCD періодично перевіряє Git репозиторій
   - Якщо зміни в `helm/` директорії або в `argocd/application.yaml`:
     - ArgoCD виявляє новий commit
     - Порівнює поточний стан кластера з бажаним станом з Git

3. **Auto-sync політика:**
   - `prune: true` - видаляє ресурси, яких більше немає в Git
   - `selfHeal: true` - автоматично відновлює стан, якщо хтось змінив його вручну
   - `allowEmpty: false` - не дозволяє порожній sync

### 5. ArgoCD синхронізує зміни з EKS кластером

**Процес синхронізації:**

1. **ArgoCD читає Helm чарт:**
   - Завантажує `helm/Chart.yaml`
   - Завантажує `helm/values.yaml`
   - Застосовує параметри з `argocd/application.yaml`:
     ```yaml
     image.repository: 451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service
     image.tag: latest
     ```

2. **Генерація Kubernetes manifests:**
   - ArgoCD виконує `helm template` з параметрами
   - Генерує Kubernetes ресурси:
     - Deployment
     - Service
     - ServiceAccount
     - Ingress (якщо увімкнено)
     - HPA (якщо увімкнено)

3. **Застосування змін до кластера:**
   - ArgoCD використовує Kubernetes API для застосування змін
   - Виконується `kubectl apply` для нових/оновлених ресурсів

### 6. Kubernetes оновлює Deployment

**Процес оновлення в EKS:**

1. **Deployment Controller виявляє зміни:**
   - Kubernetes виявляє нову версію Deployment
   - Порівнює поточний стан з бажаним

2. **Rolling Update:**
   - Kubernetes створює нові Pod'и з новим образом
   - Новий образ: `451405121207.dkr.ecr.eu-central-1.amazonaws.com/fast-api-service:latest`
   - Старі Pod'и продовжують працювати до готовності нових

3. **Readiness Probe:**
   - Kubernetes перевіряє `/docs` endpoint
   - Коли нові Pod'и готові (readiness probe успішна):
     - Трафік переключається на нові Pod'и
     - Старі Pod'и завершуються

4. **Результат:**
   - Сервіс оновлено до нової версії
   - Мінімальний downtime (rolling update)
   - 2 репліки працюють з новим кодом

### 7. Перевірка статусу

**Моніторинг процесу:**

1. **GitLab CI/CD:**
   - Перевірити статус build job в GitLab UI
   - Переконатись, що образ успішно запушено в ECR

2. **ArgoCD UI:**
   - Відкрити ArgoCD dashboard
   - Перевірити статус Application `mlops-inference-service`
   - Побачити синхронізацію в реальному часі

3. **Kubernetes:**
   ```bash
   kubectl get pods -n default
   kubectl get deployment mlops-inference-service -n default
   kubectl describe deployment mlops-inference-service -n default
   ```

4. **Тестування сервісу:**
   ```bash
   kubectl port-forward svc/mlops-inference-service 8000:8000 -n default
   curl http://localhost:8000/docs
   curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"input": "test"}'
   ```

## Сценарії оновлення

### Сценарій 1: Оновлення коду додатку

1. Змінюється `predict.py` або `requirements.txt`
2. Push в GitLab → Build job збирає новий образ
3. Образ пушиться в ECR з тегом `latest`
4. ArgoCD не виявляє змін в `helm/`, але образ `latest` оновлено
5. **Потрібно оновити Helm чарт** або змінити `image.tag` в ArgoCD application

**Рішення:** Оновити `argocd/application.yaml` з новим тегом або використати commit SHA

### Сценарій 2: Оновлення Helm чарта

1. Змінюється конфігурація в `helm/values.yaml` (наприклад, `replicaCount: 3`)
2. Push в GitLab
3. ArgoCD виявляє зміни в `helm/` директорії
4. ArgoCD автоматично синхронізує зміни
5. Kubernetes масштабує deployment до 3 реплік

### Сценарій 3: Оновлення Dockerfile

1. Змінюється `Dockerfile`
2. Push в GitLab → Build job збирає новий образ
3. Образ пушиться в ECR
4. ArgoCD використовує образ `latest`, тому автоматично підхопить новий образ
5. Kubernetes виконує rolling update

## Важливі моменти

### Безпека образів

- Образ з тегом `latest` завжди вказує на останню збірку
- Образ з commit SHA дозволяє відкотитись до конкретної версії
- Рекомендується використовувати конкретні теги для production

### Автоматизація

- ArgoCD auto-sync забезпечує автоматичне оновлення
- Self-heal відновлює стан при ручних змінах
- Prune видаляє застарілі ресурси

### Моніторинг

- ArgoCD UI показує статус синхронізації
- Kubernetes events показують процес оновлення
- GitLab CI/CD показує статус збірки

## Час виконання

- **Build job:** 2-5 хвилин (залежить від розміру образу)
- **ArgoCD sync:** 3-5 хвилин (інтервал перевірки + час синхронізації)
- **Kubernetes rolling update:** 1-3 хвилини (залежить від кількості реплік)
- **Загальний час:** 6-13 хвилин від push до повного редеплою

