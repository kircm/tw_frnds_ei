import os

missing_env_vars = []

APP_KEY = os.getenv("TW_FRNDS_EI_APP_KEY")
if not APP_KEY:
    missing_env_vars.append("TW_FRNDS_EI_APP_KEY")

APP_SECRET = os.getenv("TW_FRNDS_EI_APP_SECRET")
if not APP_SECRET:
    missing_env_vars.append("TW_FRNDS_EI_APP_SECRET")

if len(missing_env_vars) > 0:
    message = f"Missing env vars: {missing_env_vars}"
    raise ValueError(message)
