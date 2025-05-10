class Endpoints:
    AUTH_SIGNUP = "/auth/signup"
    AUTH_LOGIN = "/auth/login"

    RATE_LIMIT_GET = "/rate-limit/{username}"
    RATE_LIMIT_SET = "/rate-limit/{username}/set"
    RATE_LIMIT_UPDATE = "/rate-limit/{username}/update"

    IMAGE_BUILD_ADVANCED = "/docker/images/build"
    IMAGE_BUILD_FROM_GITHUB = "/docker/images/github-build"
    DOCKER_REGISTRY_LOGIN = "/docker/registry/login"
    IMAGE_PUSH = "/docker/images/push"
    IMAGE_PULL = "/docker/images/pull"
    IMAGE_LIST = "/docker/images"
    IMAGE_DELETE = "/docker/images/delete"

    CONTAINER_CREATE_ADVANCED = "/docker/containers/advanced"
    CONTAINER_STOP = "/docker/containers/{container_name}/stop"
    CONTAINER_LOGS = "/docker/containers/{container_name}/logs"
    CONTAINER_LIST = "/docker/containers/list"
    CONTAINER_DETAILS = "/docker/containers/{container_name}"
    CONTAINER_DELETE = "/docker/containers/{container_name}/delete"

    VOLUME_CREATE = "/docker/volumes/create"
    VOLUME_DELETE = "/docker/volumes/{volume_name}/delete"

    ADMIN_USERS_LIST = "/admin/users"
    ADMIN_USER_DETAILS = "/admin/users/{username}"
    ADMIN_USER_DELETE = "/admin/users/{username}/delete"
    ADMIN_CONTAINERS_LIST = "/admin/containers"



