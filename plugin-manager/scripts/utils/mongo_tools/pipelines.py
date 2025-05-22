from scripts.constants.mongo_constants import pipeline_constants

disabeled_actions_pipeline = {
    "$addFields": {
        "disabledActions": {
            pipeline_constants["cond"]: {
                "if": {
                    "$or": [
                        {"$in": [pipeline_constants["deployment_status_key"], ["pending", "deploying", "scanning"]]},
                        {"$eq": ["$plugin_type", "protocols"]},
                    ]
                },
                "then": ["start", "stop", "logs"],
                "else": {
                    pipeline_constants["cond"]: {
                        "if": {"$eq": [pipeline_constants["deployment_status_key"], "failed"]},
                        "then": ["start", "stop"],
                        "else": {
                            pipeline_constants["cond"]: {
                                "if": {"$eq": [pipeline_constants["deployment_status_key"], "stopped"]},
                                "then": ["stop", "logs"],
                                "else": {
                                    pipeline_constants["cond"]: {
                                        "if": {"$eq": [pipeline_constants["deployment_status_key"], "running"]},
                                        "then": ["start"],
                                        "else": [],
                                    }
                                },
                            }
                        },
                    }
                },
            }
        }
    }
}
