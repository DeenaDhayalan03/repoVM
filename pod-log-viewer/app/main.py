from fastapi import FastAPI, HTTPException, Query
from kubernetes import client, config

app = FastAPI()


@app.get("/pods/logs")
def get_pod_logs(
        name: str = Query(...),
        namespace: str = Query("default"),
        container: str = Query(None),
):
    try:
        config.load_incluster_config()
        core_v1 = client.CoreV1Api()

        log_response = core_v1.read_namespaced_pod_log(
            name=name,
            namespace=namespace,
            container=container,
            tail_lines=50,
        )
        return {"logs": log_response}
    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
