from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="PORTFOLIO_MANAGER",
    settings_files=["settings.yaml"],
    environments=True,
    load_dotenv=True,
    env_switcher="ENV_FOR_DYNACONF",
)
