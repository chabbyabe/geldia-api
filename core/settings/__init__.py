import os

from decouple import config

# When Django imports an explicit submodule such as `core.settings.test`,
# keep the package import side-effect free so the submodule can load itself.
if os.getenv("DJANGO_SETTINGS_MODULE", "core.settings") == __name__:
    settings_environment: str = config("DJANGO_ENVIRONMENT_SETTINGS", "dev")

    if settings_environment == "dev":
        print(
            f"Detected with the settings of '{settings_environment}', "
            "running the development settings",
        )
        from .dev import *
    elif settings_environment == "prod":
        from .prod import *
        print(
            f"Detected with the settings of '{settings_environment}', "
            "running the production settings",
        )
    else:
        from .dev import *
        print(
            f"Settings with a value of '{settings_environment}' is not "
            "defined, defaulting with development settings",
        )
