# MLOps Project: End-to-End MLOps Pipeline

✅ **Реалізовано в поточній версії**:
- FastAPI inference-сервіс із ендпоінтами `/health`, `/predict`, `/metrics`.
- Логування вхідних даних та результатів.
- Drift detection у вигляді простого rule-based stub (для демонстрації механіки).
- Prometheus-метрики (requests, latency, drift counter) та scrape через pod annotations.
- GitOps деплой через ArgoCD (App-of-Apps), розділення на namespaces: `serving`, `training`, `observability`.
- MLflow + Postgres підняті як training-plane для трекінгу експериментів (доступ через port-forward).

⚠️ **Архітектурні рішення та обмеження**

Через використання **AWS Free Tier** та ліміти вузлів **t3.small**:
1. **Ресурсний менеджмент**: Компоненти Loki та Promtail були видалені після тестів, оскільки вони призводили до помилки Too many pods (перевищення ліміту IP-адрес/подів на один вузол).
2. **Мережевий доступ**: Доступ до сервісів здійснюється через kubectl port-forward. Використання AWS Load Balancer вимкнено для запобігання зайвих витрат.
3. **CI/CD Retrain**: GitLab CI працює в **Demo/Mock режимі**. Оскільки MLflow знаходиться всередині приватної мережі EKS, пайплайн імітує успішне тренування та фокусується на кроках збірки образу та оновлення версії в Git (GitOps-пуш). Оскільки AWS Load Balancer вимкнено, не можемо зробити MLflow публічним.

---

## Структура репозиторію (фактична)
```
aiops-quality-project/
├── app/
│   ├── main.py                    # FastAPI inference + metrics + drift stub
│   ├── requirements.txt
│   └── argocd/
│       ├── app-of-apps.yaml       # App-of-Apps entrypoint
│       └── applications/          # ArgoCD child apps (serving/training/observability)
├── model/
│   ├── train.py                   # Training + MLflow model registry (локально через port-forward)
│   └── requirements.txt
├── helm/
│   ├── inference-api/             # Helm chart: inference service
│   ├── mlflow/                    # Wrapper chart: mlflow community chart
│   └── postgres/                  # Helm chart: postgres for mlflow backend store
├── terraform/
│   ├── ecr/
│   └── eks/
├── Dockerfile
├── .gitlab-ci.yml
└── README.md
```


## Етап 1: Інфраструктура як код (Terraform ECR)

**Дія:** Створення реєстру AWS ECR для зберігання Docker-образів сервісу інференсу.

```bash
cd terraform/ecr
terraform init
terraform apply -auto-approve
```

![alt text](screens/0.%20terra_apply.png)

---

## Етап 2: Розробка та локальна перевірка API

**Дія:** Створення Docker-образу FastAPI сервісу та його тестування.

```bash
# Збірка образу
docker build -t inference-api:v0.1.0 .
```

![alt text](screens/1.%20docker_build.png)

```bash
# Локальний запуск та перевірка Health-check
docker run -p 8080:8080 inference-api:v0.1.0
```

![alt text](screens/2.%20docker_local_check.png)

![alt text](screens/3.%20docker_inference_check.png)

---

## Етап 3: Підготовка Helm-чарту

**Дія:** Створення Helm-шаблонів для Inference-api, MLflow, Postgres.

---

## Етап 4: Розгортання EKS Кластера

**Дія:** Створення VPC та керованого Kubernetes кластера в AWS.

```bash
cd terraform/eks
terraform apply -auto-approve
aws eks update-kubeconfig --region eu-north-1 --name aiops-quality-cluster --profile hannadunska-fp-mlops
```

![alt text](screens/5.%20eks_cluster_apply.png)

![alt text](screens/6.%20kubectl_get_nodes.png)

---

## Етап 5: Початковий деплой сервісів

**Дія:** Ручний деплой для первинної перевірки чартів та бази даних.

```bash
# Helm chart deploy
helm upgrade --install inference-api ./helm/inference-api -n serving
```
![alt text](screens/7.%20helm_chart_deploy.png)

### Postgres як база даних для MLflow

![alt text](screens/8.%20postgres_training.png)

---

## Етап 6: MLflow та Артефакти (Training Plane)

**Дія:** Налаштування S3 для зберігання моделей та запуск MLflow Tracking Server.

```bash
# Створення S3 бакета
aws s3 mb s3://$MLFLOW_BUCKET --region $AWS_REGION --profile $AWS_PROFILE
```

![alt text](screens/9.%20s3_bucket.png)

```bash
# Mlflow deploy
helm upgrade --install mlflow ./helm/mlflow -n training

# Доступ до MLflow UI
kubectl -n training port-forward svc/training-mlflow 5000:5000
```

![alt text](screens/9.%20mlflow_training.png)

![alt text](screens/12.%20ml_flow_working.png)

---

## Етап 7: GitOps та ArgoCD

**Дія:** Впровадження GitOps-процесу через ArgoCD для автоматичної синхронізації стану репозиторію з кластером.

```bash
# Створення Namespace та деплой App-of-Apps
kubectl apply -f app/argocd/app-of-apps.yaml
```

![alt text](screens/14.%20prometheus_ui.png)

---

## Етап 8: Робота сервісу та Детекція Дрейфу

**Дія:** Виконання прогнозів та перевірка механізму виявлення дрейфу даних.

```bash
# Тестування передбачень через Port-forward
kubectl -n serving port-forward svc/inference-api 8080:80
```

**Результати запитів:**

- **Drift = False (Нормальні дані)**:
    
    ![alt text](screens/20.%20drift_false.png)
    
- **Drift = True (Аномальні дані)**:
    
    ![alt text](screens/21.%20drift_true.png)
    
    

---

## Етап 9: Моніторинг (Prometheus)

**Дія:** Збір та візуалізація метрик роботи моделі.


![alt text](screens/23.%20prometheus.png)

![alt text](screens/23.%20prometheus_latency.png)

![alt text](screens/23.%20prometheus_drift.png)

Були виключені: Loki & Promtail
![alt text](screens/16.%20too_man_pods.png)


---

## Етап 10: Retraining Loop (GitLab CI)

**Дія:** Автоматизація перенавчання моделі та оновлення продуктового середовища.

1. **Тренування та реєстрація моделі:**
    
    ![alt text](screens/19.%20model_train_and_promotion.png)
    
2. **Запуск GitLab CI Пайплайну:**
- **Automation (що CI робить автоматично):**
  - Збирає новий Docker-образ inference-сервісу
  - Push-ить образ в ECR реєстр
  - Оновлює тег образу в Helm values.yaml через CI-бот (bump версії)
  - Робить git commit та push змін у репозиторій
  - ArgoCD автоматично виявляє зміни та деплоїть нову версію в кластер через automated sync policy
- **Обмеження (що CI не може зробити):**
  - Не може запускати тренування моделі в MLflow, допоки MLflow знаходиться в приватній мережі EKS
  - Тренування моделі виконується вручну/локально через port-forward до MLflow

    ![alt text](screens/25.%20cicd_gitlab.png)

    ![alt text](screens/26.%20argo_cd_proof.png)
    

---

## Результати

**Технічні результати впровадження**

**1. Inference & API Layer**
- **Deployment**: FastAPI сервіс розгорнуто в K8s (namespace: serving) з налаштованими Liveness/Readiness probes.
- **Interface**: Реалізовано REST API з ендпоінтами `/predict`, `/health` та `/metrics`.
- **Logic**: API успішно обробляє вхідні JSON-тензори та повертає передбачення разом із прапором `drift_detected`, що дозволяє інтегрувати логіку дрейфу безпосередньо у відповідь сервісу.
- **Connectivity**: Підтверджено коректну маршрутизацію трафіку до подів через Service (ClusterIP) при використанні port-forward.

**2. GitOps & CD (ArgoCD)**
- **Pattern**: Впроваджено підхід App-of-Apps. ArgoCD автоматично синхронізує стан Helm-чартів із репозиторію в кластер.
- **Lifecycle**: Будь-яка зміна версії образу (image tag) у Git автоматично ініціює RollingUpdate деплойменту без ручного використання kubectl.
- **Isolation**: Ресурси логічно розділені на рівні Namespace: `serving` (інференс), `training` (MLflow, Postgres) та `observability` (Prometheus).

**3. Monitoring & Observability**
- **Metrics**: Реалізовано Prometheus-експортер. Окрім стандартних системних метрик (Python GC, Memory), збираються кастомні бізнес-метрики: затримка (latency) та статус дрейфу.
- **Alerting Foundation**: Ендпоінт `/metrics` інтегровано в Prometheus targets через pod annotations (`prometheus.io/scrape: "true"`), що дозволяє будувати Dashboard у Grafana та налаштовувати алертінг на аномальні значення дрейфу.

**4. CI/CD Retraining Loop**
- **Automation**: CI автоматично збирає новий Docker-образ, push-ить в ECR, оновлює Helm-чарт (bump версії) та пушить зміни в Git. ArgoCD автоматично синхронізує нову версію в кластер.
- **GitOps Integration**: Зміни версії образу в Git автоматично ініціюють RollingUpdate деплойменту без ручного втручання, демонструючи автоматизацію CI/CD → GitOps для deployment частини.
- **Infrastructure**: Створено стабільний Training Plane (MLflow + Postgres + S3), що забезпечує збереження артефактів та трекінг експериментів поза межами життя окремих подів.




