from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class DeploymentContainer(BaseModel):
    name: str = Field(..., description="Name of the container")
    image: str = Field(..., description="Container image to use")
    ports: Optional[List[int]] = Field(default=None, description="List of exposed container ports")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables for the container")


class DeploymentCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the deployment")
    namespace: str = Field(..., description="Kubernetes namespace for the deployment")
    replicas: int = Field(..., ge=1, description="Number of desired pod replicas")
    containers: List[DeploymentContainer] = Field(..., description="List of containers in the deployment")
    labels: Optional[Dict[str, str]] = Field(default=None, description="Optional labels for the deployment")


class DeploymentScaleRequest(BaseModel):
    replicas: int = Field(..., ge=0, description="New number of replicas to scale the deployment to")
