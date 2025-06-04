from fastapi import FastAPI, HTTPException
from kubernetes import client, config

app = FastAPI()

@app.get("/pods/{pod_name}/logs")
def get_pod_logs(pod_name: str, namespace: str = "default"):
    try:
        config.load_incluster_config()
        core_v1 = client.CoreV1Api()
        log_response = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=50,
        )
        return {"logs": log_response}
    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
