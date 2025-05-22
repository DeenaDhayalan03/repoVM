from fastapi.encoders import jsonable_encoder
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.dynamic import DynamicClient

from scripts.config import EnvConf, IstioGateway
from scripts.constants import ErrorMessages, IgnoreSecrets, VolumeMount
from scripts.db.mongo import mongo_client
from scripts.db.mongo.ilens_db.collections.plugin_state import PluginState
from scripts.exceptions import (
    DeploymentException,
    PodException,
    ServiceException,
    VirtualServiceException,
)
from scripts.logging import logger
from scripts.schema import DeleteConfig, DeployConfig, PodStatus


class KubernetesHandler:
    def __init__(
        self,
        deploy_data: DeployConfig = None,
        **kwargs,
    ):
        """
        The __init__ function is called when the class is instantiated.
        It sets up the instance variables for this particular object.


        :param self: Represent the instance of the class
        :param app_name:str: Name the application
        :param image:str: Set the image name of the docker container
        :param app_id:str: Create a unique name for the service
        :param env_var:List[Dict]: Pass in environment variables to the pod
        :param namespace:str: Specify the namespace in which
                              the application should be deployed
        :param port:int: Specify the port that the application will run on
        :param replicas:int: Set the number of replicas for a given deployment
        :return: None
        :doc-author: Sayed Imran
        """
        try:
            if EnvConf.env == "local":
                config.load_kube_config(config_file="scripts/conf/k3s.yaml")
                logger.info("Loading local kubernetes config")
            else:
                config.load_incluster_config()
                logger.info("Loading in-cluster kubernetes config")
        except Exception as e:
            logger.error("Error loading Kubernetes config: %s", e)
            raise e.args from e
        self.k8s_client = client.ApiClient()
        self.deploy_data = deploy_data or DeployConfig()
        self.app_name = self.deploy_data.app_name.replace("_", "-").lower()
        self.app_id = self.deploy_data.app_id.replace("_", "-").lower()
        self.project_id = self.deploy_data.project_id.replace("_", "-").lower()
        self.app_version = self.deploy_data.app_version.replace("_", "-").lower()
        self.namespace = EnvConf.namespace
        self.name = f"{self.app_name}-{self.app_id}"
        self.service = f"{self.name}.{self.namespace}.svc.cluster.local"
        self.path = f"/plugin/{self.project_id}/{self.app_name}/api/"
        self.dynamic_client = DynamicClient(self.k8s_client)
        self.deployment_resource = client.AppsV1Api(self.k8s_client)
        self.api_v1_resource = client.CoreV1Api(self.k8s_client)
        self.virtualservice_resource = self.dynamic_client.resources.get(
            api_version="networking.istio.io/v1alpha3", kind="VirtualService"
        )
        self.plugin_state = PluginState(mongo_client=mongo_client)
        self.gateway_proxy = "/gateway"
        self.proxy = f"{self.gateway_proxy}{self.path}"
        self.auth = kwargs.get("auth", False)
        env_var = jsonable_encoder(self.deploy_data.env_var) or []
        env_var = self.process_env_config(env_var)
        env_var.append({"name": "PROXY", "value": f"/gateway{self.path[:-1]}"})
        self.env = env_var

    def create_deployment(self):
        """
        The create_deployment function creates a deployment in the Kubernetes cluster.
            Args:
                app_name (str): The name of the application to be deployed.
                app_id (str): The ID of the application to be deployed.
                path (str): The path where this plugin will be accessible
                    from outside world, e.g., /api/v2/plugins/my-plugin/.
                    This is used for routing traffic to this plugin's service using
                    Istio VirtualService resource type.
                    If you don't want your plugin exposed externally, set it as None

        :param self: Access the attributes and methods of the class in python
        :return: The name of the deployment, the service and the path
        :doc-author: Sayed Imran
        """

        try:
            data = {
                "app_name": self.app_name,
                "app_id": self.app_id,
                "auth": self.auth,
                "proxy_path": self.path,
                "namespace": self.namespace,
                "image": self.deploy_data.image,
                "env_var": self.env,
                "port": self.deploy_data.port,
                "app_version": self.app_version,
                "resources": jsonable_encoder(self.deploy_data.resources),
            }
            if self.plugin_state.get_plugin_state(app_name=self.app_name, app_id=self.app_id):
                return self.update_deployment()
            labels = {
                "app": self.name,
                "auth": "enabled" if self.auth else "disabled",
                "sidecar.istio.io/inject": "true" if self.auth else "false",
            }
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": self.name, "namespace": self.namespace},
                "spec": {
                    "replicas": self.deploy_data.resources.replicas,
                    "selector": {"matchLabels": labels},
                    "template": {
                        "metadata": {
                            "labels": labels,
                            "annotations": {
                                "deployed.timestamp": str(int(time.time() * 1000)),
                            },
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": self.name,
                                    "image": self.deploy_data.image,
                                    "imagePullPolicy": "Always",
                                    "resources": {
                                        "requests": {
                                            "memory": self.deploy_data.resources.memory_request,
                                            "cpu": self.deploy_data.resources.cpu_request,
                                        },
                                        "limits": {
                                            "memory": self.deploy_data.resources.memory_limit,
                                            "cpu": self.deploy_data.resources.cpu_limit,
                                        },
                                    },
                                    "ports": [{"containerPort": self.deploy_data.port}],
                                    "env": self.env,
                                    "volumeMounts": [
                                        {
                                            "mountPath": "/code/data",
                                            "name": "core-volumes",
                                            "subPath": "core-volumes",
                                        },
                                    ],
                                    "securityContext": {
                                        "runAsNonRoot": True,
                                        "readOnlyRootFilesystem": True,
                                        "runAsUser": 1000,
                                        "capabilities": {"drop": ["ALL"]},
                                    },
                                }
                            ],
                            "imagePullSecrets": [{"name": EnvConf.image_pull_secret}],
                            "volumes": [
                                VolumeMount.volume,
                            ],
                        },
                    },
                },
            }

            self.deployment_resource.create_namespaced_deployment(
                namespace=self.namespace, body=deployment, pretty=True
            )
            logger.info("Deployment created successfully")
            service = self.create_service()
            self.create_virtual_service()
            self.plugin_state.create_plugin_state(data)
            return self.name, service, self.proxy
        except ApiException as e:
            logger.error("Error creating deployment: %s", e)
            raise DeploymentException(e.args) from e

    def update_deployment(self):
        """
        This function updates the deployment with a new image and number of replicas.
            Args:
                self (object): The object that contains
                               all the variables for this function.
            Returns:
                name (str): The name of the deployment to be updated.
                service (str): The service associated with this deployment,
                               which is used to create an ingress rule.

        :param self: Bind the method to an object
        :return: The name, service and path of the deployment
        :doc-author: Sayed Imran
        """
        logger.info("Updating deployment")
        deployment = self.deployment_resource.read_namespaced_deployment(name=self.name, namespace=self.namespace)
        deployment.spec.replicas = self.deploy_data.resources.replicas
        for container in deployment.spec.template.spec.containers:
            if container.name == self.name:
                container.image = self.deploy_data.image
        deployment.spec.template.spec.containers[0].env = self.env
        deployment.spec.template.spec.containers[0].resources = {
            "requests": {
                "memory": self.deploy_data.resources.memory_request,
                "cpu": self.deploy_data.resources.cpu_request,
            },
            "limits": {
                "memory": self.deploy_data.resources.memory_limit,
                "cpu": self.deploy_data.resources.cpu_limit,
            },
        }
        current_timestamp_ms = str(int(time.time() * 1000))
        deployment.spec.template.metadata.annotations = deployment.spec.template.metadata.annotations or {}
        deployment.spec.template.metadata.annotations["deployed.timestamp"] = current_timestamp_ms
        self.deployment_resource.patch_namespaced_deployment(name=self.name, namespace=self.namespace, body=deployment)
        logger.info("Deployment updated with image: %s", self.deploy_data.image)
        self.update_service()
        self.plugin_state.update_plugin_state(
            app_name=self.app_name,
            app_id=self.app_id,
            data={
                "image": self.deploy_data.image,
                "app_version": self.app_version,
                "replicas": self.deploy_data.resources.replicas,
            },
        )
        return self.name, self.service, self.proxy

    def update_service(self):
        """
        The update_service function updates the service with a new port number.
            Args:
                self (object): The object that contains
                               all the variables for this function.
            Returns:
                name (str): The name of the service to be updated.
                service (str): The service associated with this deployment,
                               which is used to create an ingress
                               rule for it in Kubernetes.

        :param self: Bind the method to an object
        :return: The name, service and path of the service
        :doc-author: Sayed Imran
        """
        logger.info("Updating service")
        body = [
            {
                "op": "replace",
                "path": "/spec/ports/0/targetPort",
                "value": self.deploy_data.port,
            }
        ]
        self.api_v1_resource.patch_namespaced_service(name=self.name, namespace=self.namespace, body=body, pretty=True)
        logger.info("Service updated with port: %s", self.deploy_data.port)
        return self.service

    def create_service(self):
        """
        The create_service function creates a service in the specified namespace.
            Args:
                name (str): The name of the service to be created.
                namespace (str): The namespace where the service will be created.
                port (int): The port number for which traffic will be
                            routed to pods with this label selector.

        :param self: Refer to the current object
        :return: A f-string, which is a formatted string
        :doc-author: Sayed Imran
        """

        try:
            service = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": self.name, "namespace": self.namespace},
                "spec": {
                    "selector": {"app": self.name},
                    "ports": [
                        {
                            "protocol": "TCP",
                            "port": self.deploy_data.port,
                            "targetPort": self.deploy_data.port,
                        }
                    ],
                },
            }
            self.api_v1_resource.create_namespaced_service(namespace=self.namespace, body=service)
            logger.info("Service created successfully")
            return f"{self.name}.{self.namespace}.svc.cluster.local"
        except ApiException as e:
            logger.error("Error creating service: %s", e)
            raise ServiceException(e.args) from e

    def create_virtual_service(self):
        """
        This function creates a virtual service for the FastAPI application.
            Args:
                name (str): The name of the FastAPI application.
                namespace (str): The namespace in which to
                                 create the virtual service.
                path (str): The path at which to expose
                            the FastAPI application, e.g., /fastapi/v0/.
            Returns:

        :param self: Refer to the object itself
        :return: A tuple of true and the path
        :doc-author: Sayed Imran
        """
        try:
            virtual_service = {
                "apiVersion": "networking.istio.io/v1alpha3",
                "kind": "VirtualService",
                "metadata": {"name": self.name, "namespace": self.namespace},
                "spec": {
                    "gateways": [IstioGateway.istio_gateway],
                    "hosts": ["*"],
                    "http": [
                        {
                            "match": [{"uri": {"prefix": self.path}}],
                            "rewrite": {"uri": "/"},
                            "route": [
                                {
                                    "destination": {
                                        "host": self.service,
                                        "port": {"number": self.deploy_data.port},
                                    }
                                }
                            ],
                        }
                    ],
                },
            }
            self.virtualservice_resource.create(body=virtual_service)
            logger.info("Virtual service created successfully")
            return self.path
        except ApiException as e:
            logger.error("Error creating virtual service: %s", e)
            raise VirtualServiceException(e.args) from e

    def delete_deployment(self, delete_config: DeleteConfig):
        """
        This function deletes the deployment,
        service and virtual service for a given app.


        :param self: Access the attributes and methods of the class
        :return: The name of the deployment, the service and the path
        :doc-author: Sayed Imran
        """

        try:
            app_name = delete_config.app_name.replace("_", "-").lower()
            app_id = delete_config.app_id.replace("_", "-").lower()
            self.deployment_resource.delete_namespaced_deployment(
                name=f"{app_name}-{app_id}", namespace=self.namespace, pretty=True
            )
            self.plugin_state.delete_plugin_state(app_name=app_name, app_id=app_id)
            logger.info("Deployment deleted successfully")
            service = self.delete_service(app_name=app_name, app_id=app_id)
            self.delete_virtual_service(app_name=app_name, app_id=app_id)
            return f"{app_name}-{app_id}", service, self.proxy
        except ApiException as e:
            logger.error("Error deleting deployment: %s", e)
            raise DeploymentException(e.args) from e

    def delete_service(self, app_name: str, app_id: str):
        """
        This function deletes a service from the Kubernetes cluster.
                Args:
                    self (object): The object instance of the class.

        :param self: Represent the instance of the class
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            self.api_v1_resource.delete_namespaced_service(
                name=f"{app_name}-{app_id}", namespace=self.namespace, pretty=True
            )
            logger.info("Service deleted successfully")
            return f"{self.name}.{self.namespace}.svc.cluster.local"
        except ApiException as e:
            logger.error("Error deleting service: %s", e)
            raise ServiceException(e.args) from e

    def delete_virtual_service(self, app_name: str, app_id: str):
        """
        This function deletes a virtual service.
                Args:
                    self (object): The object instance of the class.

        :param self: Represent the instance of a class
        :return: The path of the virtual service
        :doc-author: Sayed Imran
        """

        try:
            self.virtualservice_resource.delete(name=f"{app_name}-{app_id}", namespace=self.namespace)
            logger.info("Virtual service deleted successfully")
            return self.path
        except ApiException as e:
            logger.error("Error deleting virtual service: %s", e)
            raise VirtualServiceException(e.args) from e

    def deployment_status(self, status_config: PodStatus):
        """
        This function returns the status of a deployment.
            If the deployment is not fully available,
            it will return how many replicas are available out of how many desired.
            If the deployment is fully available,
            it will return which ReplicaSet pods are running under.

        :param self: Access the attributes of the class
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            deployment = self.deployment_resource.read_namespaced_deployment(
                name=f'{status_config.app_name.replace("_","-").lower()}-{status_config.app_id.replace("_","-").lower()}',
                namespace=self.namespace,
                pretty=True,
            )
            available_replicas = deployment.status.available_replicas
            desired_replicas = deployment.spec.replicas
            if available_replicas is None or desired_replicas is None:
                return "Deployment in progress"
            elif available_replicas == desired_replicas:
                deployment.status.conditions[1].message.split(" ")[1]
                return "Pods are running for the deployment"
            else:
                return f"Deployment is not fully available. {available_replicas}/{desired_replicas} replicas are available."

        except ApiException as e:
            logger.error(f"{ErrorMessages.error_reading_deployment}: %s", e)
            raise DeploymentException(e.args) from e

    async def deployments_status(self, plugin_list: list[str]):  # NOSONAR
        """
        The deployments_status function returns a list of dictionaries, each containing the status of a deployment.
        The dictionary contains the following keys:
            plugin: The detail of the plugin as it appears in the plugins table.
            status: A string indicating whether or not all pods are running, if there is an error with one or more pods,
                    if some pods are still being created (in progress), or if no deployment was found for that plugin.
                    Possible values include "completed", "error", "in_progress" and "not_found". If there is an error with one
                    pod but the rest are running, the status will be "error".
            replicas: The number of replicas for the deployment.
            pods: A list of dictionaries, each containing the status of a pod. Each dictionary contains the following keys:
                pod_name: The name of the pod.
                containers: A list of dictionaries, each containing the status of a container. Each dictionary contains the following keys:
                    container_name: The name of the container.
                    image: The image of the container.
                    status: A string indicating the status of the container. Possible values include "running", "in_progress", "error", "terminated" and "unknown".
                    reason: The reason for the error, if the status is "error".
        :param self: Bind the method to an object
        :param plugin_list: list[str]: Pass in a list of plugins
        :return: A list of dictionaries
        :doc-author: Sayed Imran
        """
        statuses = []
        for index, plugin in enumerate(plugin_list):
            container_statuses = []
            statuses.append({"plugin": plugin, "status": "in_progress", "pods": []})
            deployment = plugin.replace("_", "-").lower()
            try:
                deployment_status = self.deployment_resource.read_namespaced_deployment(
                    name=deployment, namespace=self.namespace, pretty=True, async_req=True
                ).get()
                statuses[index]["replicas"] = deployment_status.spec.replicas
                labels = deployment_status.spec.template.metadata.labels
                label_selector = ",".join([f"{key}={value}" for key, value in labels.items()])
                pods = self.api_v1_resource.list_namespaced_pod(
                    namespace=self.namespace,
                    pretty=True,
                    label_selector=label_selector,
                    async_req=True,
                ).get()
                for npod, pod in enumerate(pods.items):
                    statuses[index]["pods"].append({"pod_name": pod.metadata.name, "containers": []})
                    for container in pod.status.container_statuses:
                        status = self.get_container_status(container)
                        container_statuses.append(status)
                        statuses[index]["pods"][npod]["containers"].append(
                            {
                                "container_name": container.name,
                                "image": container.image,
                                "status": status,
                            }
                        )
                        if status == "error":
                            statuses[index]["pods"][npod]["containers"][-1]["reason"] = (
                                container.state.waiting.reason or container.state.terminated.reason
                            )
                            statuses[index]["pods"][npod]["containers"][-1]["message"] = (
                                container.state.waiting.message or container.state.terminated.message
                            )
                if all(status == "running" for status in container_statuses):
                    statuses[index]["status"] = "completed"
                elif "in_progress" in container_statuses:
                    statuses[index]["status"] = "in_progress"
                elif "error" in container_statuses:
                    statuses[index]["status"] = "error"

            except ApiException as e:
                logger.error(f"{ErrorMessages.error_reading_deployment}: %s", deployment)
                logger.error(e)
                statuses[index]["status"] = "not_found"
        return statuses

    def get_container_status(self, container):
        """
        The get_container_status function returns the status of a container.
            Args:
                container : A  container object to check the status

        :param self: Represent the instance of the class
        :param container: Get the status of a container
        :return: A string that is the status of the container
        :doc-author: Sayed Imran
        """
        if container.state.running:
            return "running"
        elif container.state.waiting and container.state.waiting.reason == "ContainerCreating":
            return "in_progress"
        elif container.state.waiting:
            return "error"
        elif container.state.terminated:
            return "terminated"
        else:
            return "unknown"

    def get_logs(self, app_name: str, lines: int = 100):
        """
        The get_logs function returns the logs of a pod.
            Args:
                app_name (str): The name of the application to get logs for.
                lines (int): The number of lines to return from the log file. Defaults to 10 if not specified.

        :param self: Refer to the current object
        :param app_name: str: Specify which pod you want to get the logs from
        :param lines: int: Specify the number of lines to return
        :return: A string of logs
        :doc-author: Sayed Imran
        """

        try:
            pods = self.api_v1_resource.list_namespaced_pod(
                namespace=self.namespace, pretty=True, label_selector=f"app={app_name}"
            )
            logs = ""
            for count, pod in enumerate(pods.items):
                logs += f"replica-{count+1} | "
                logs += self.api_v1_resource.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=self.namespace,
                    pretty=True,
                    tail_lines=lines,
                )
                logs = logs.replace("\n", f"<br/>replica-{count+1} | ")
                logs = logs.rstrip(f"<br/>replica-{count+1} | ")
                logs += "<br/>"

            return logs

        except ApiException as e:
            logger.error("Error reading pod: %s", e)
            raise PodException(e.args) from e

    def start_stop_deployment(self, plugin: str, action: str):
        """
        The start_stop_deployment function is used to start or stop a deployment.
            Args:
                plugin (str): The name of the deployment to be started/stopped.
                action (str): The action that should be performed on the deployment, either running or stopped.

        :param self: Refer to the object itself
        :param plugin: str: Pass the name of the deployment to be started or stopped
        :param action: str: Determine whether to start or stop the deployment
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            deployment = self.deployment_resource.read_namespaced_deployment(
                name=plugin, namespace=self.namespace, pretty=True
            )
            app_id = plugin.split("-")[-1].lower()
            deployment_details = self.plugin_state.get_plugin_by_id(app_id=app_id)
            if action == "running":
                deployment.spec.replicas = (
                    deployment_details.get("replicas", None) or deployment_details["resources"]["replicas"] or 1
                )
            elif action == "stopped":
                deployment.spec.replicas = 0
            self.deployment_resource.patch_namespaced_deployment(
                name=plugin, namespace=self.namespace, body=deployment, pretty=True
            )

            return f"Deployment {plugin} started successfully"

        except ApiException as e:
            logger.error(f"{ErrorMessages.error_reading_deployment}: %s", e)
            raise DeploymentException(e.args) from e

    def get_secrets_from_namespace(self):
        """
        The get_secrets_from_namespace function returns all secrets in a namespace.
            Args:
                namespace (str): The namespace from which to get secrets.

        :param self: Refer to the object itself
        :return: A list of secrets
        :doc-author: Sayed Imran
        """

        try:
            ignore_secrets_type = "".join([f"type!={secret_type}," for secret_type in IgnoreSecrets.secret_type])
            secrets = self.api_v1_resource.list_namespaced_secret(
                namespace=self.namespace,
                field_selector=ignore_secrets_type[:-1],
                pretty=True,
            )
            secret_list = [secret.metadata.name.upper() for secret in secrets.items]
            for secret in IgnoreSecrets.secret_list:
                if secret in secret_list:
                    secret_list.remove(secret)
            return secret_list

        except ApiException as e:
            logger.error("Error reading secrets: %s", e)
            raise e

    def create_secret(self, secret_name: str, data: dict):
        """
        The create_secret function creates a secret in a namespace.
            Args:
                namespace (str): The namespace in which to create the secret.
                secret_name (str): The name of the secret to be created.
                data (dict): The data to be stored in the secret.

        :param self: Refer to the object itself
        :param secret_name: str: Pass the name of the secret to be created
        :param data: dict: Pass the data to be stored in the secret
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            secret = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": secret_name.replace("_", "-").lower(), "namespace": self.namespace},
                "type": "Opaque",
                "data": data,
            }
            self.api_v1_resource.create_namespaced_secret(namespace=self.namespace, body=secret)
            logger.info("Secret created successfully")
            return f"Secret {secret_name} created successfully"

        except ApiException as e:
            logger.error("Error creating secret: %s", e)
            raise e

    def generate_secrets(self, key: str):
        """
        The generate_secrets function generates secrets.
            Args:
                key (str): The key of the secret to be generated.

        :param self: Refer to the object itself
        :param key: str: Pass the key of the secret to be generated
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            return {
                "name": key,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": key.replace("_", "-").lower(),
                        "key": key,
                    }
                },
            }

        except Exception as e:
            logger.error("Error generating secret: %s", e)
            raise e

    def delete_secret(self, name: str):
        """
        The delete_secret function deletes a secret from a namespace.
            Args:
                namespace (str): The namespace from which to delete the secret.
                name (str): The name of the secret to be deleted.

        :param self: Refer to the object itself
        :param name: str: Pass the name of the secret to be deleted
        :return: A string
        :doc-author: Sayed Imran
        """

        try:
            self.api_v1_resource.delete_namespaced_secret(
                name=name.replace("_", "-").lower(), namespace=self.namespace, pretty=True
            )
            logger.info("Secret deleted successfully")
            return f"Secret {name} deleted successfully"

        except ApiException as e:
            logger.error("Error deleting secret: %s", e)
            raise e

    def process_env_config(self, env_configs: list):
        try:
            env_vars = []
            for env_config in env_configs:
                if env_config.get("type", None) == "kubernetes_secrets":
                    env_vars.append(
                        {
                            "name": env_config["key"],
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": env_config["key"].replace("_", "-").lower(),
                                    "key": env_config["value"].replace("-", "_").upper(),
                                }
                            },
                        }
                    )
                elif env_config.get("type", None) in ["text", "secure"]:
                    env_vars.append({"name": env_config["key"], "value": env_config["value"]})
                else:
                    env_vars.append({"name": env_config["key"], "value": env_config["value"]})
            return env_vars
        except Exception as e:
            logger.error("Error processing env config: %s", e)
            raise e
