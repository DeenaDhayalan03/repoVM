import os

from fastapi.testclient import TestClient

from main import app
from scripts.services.v1.schemas import Plugin

client = TestClient(app)


def test_save_plugin():
    payload = Plugin(
        name="Test Plugin",
        configurations=[
            {"value": "0.0.0.0", "key": "HOST", "type": "text"},
            {"value": "MONGO-URI", "key": "MONGO_URI", "type": "kubernetes_secret"},
        ],
        advancedConfiguration={
            "headerContent": [
                {"label": "Property", "key": "propertyLabel"},
                {"label": "Description", "key": "description"},
                {"label": "Input", "key": "input"},
            ],
            "bodyContent": [
                {
                    "property": "replicas",
                    "description": "Define the number of replicas/instances for a plugin",
                    "propertyLabel": "Replicas",
                    "input": 2,
                }
            ],
        },
        plugin_type="microservice",
        industry=["YrHTmdZnewRMUeViLXTWjs"],
        git_url="https://gitlab-pm.knowledgelens.com/surendra.prasath/sample-api.git",
        git_branch="master",
        git_username="Imran",
        git_access_token=os.getenv("GIT_ACCESS_TOKEN"),
        registration_type="git",
        information={"description": "This is a test plugin", "version": "1.0.0"},
    )
    client.post("/api/v1/plugins", json=payload.model_dump())
