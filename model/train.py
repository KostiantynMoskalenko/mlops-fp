import os
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT", "iris_rf_experiment")
MODEL_NAME = os.getenv("MODEL_NAME", "iris_rf_model")

PROMOTE_TO_PROD = os.getenv("PROMOTE_TO_PROD", "true").lower() == "true"

def main():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    X, y = load_iris(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

    with mlflow.start_run() as run:
        clf = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
        clf.fit(X_train, y_train)

        acc = accuracy_score(y_test, clf.predict(X_test))
        mlflow.log_metric("accuracy", acc)

        # Register model in Model Registry
        model_info = mlflow.sklearn.log_model(
            sk_model=clf,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )

        print(f"Run ID: {run.info.run_id}")
        print(f"Registered model name: {MODEL_NAME}")
        print(f"Model URI: {model_info.model_uri}")

        if PROMOTE_TO_PROD:
            client = MlflowClient()
            # Find latest version created by this run
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            # Pick the newest by version number
            latest = max(versions, key=lambda v: int(v.version))
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=latest.version,
                stage="Production",
                archive_existing_versions=True
            )
            print(f"Promoted {MODEL_NAME} v{latest.version} to Production")

if __name__ == "__main__":
    main()
