try:
    from dotenv import load_dotenv

    load_dotenv()

    from scripts.log import init_logger

    init_logger()

except ImportError:
    import sys

    sys.exit(1)


from ut_security_util import FastAPIConfig, generate_fastapi_app

import __version__
from scripts.config import Services as ServiceConf
from scripts.services import router
from scripts.utils import preflight

app_config = FastAPIConfig(
    title="plugin manager",
    description="A suite of services to manage plugins in UnifyTwin",
    version=__version__.__version__,
    docs_url=ServiceConf.SW_DOCS_URL,
    root_path="/plugin-manager",
    openapi_url=ServiceConf.SW_OPENAPI_URL,
)

preflight.run()

app = generate_fastapi_app(
    app_config=app_config,
    routers=[router],
    project_name="plugin-manager",
)
