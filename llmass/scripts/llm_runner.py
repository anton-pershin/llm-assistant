import logging
from pathlib import Path

import hydra
from hydra.utils import instantiate 
from omegaconf import DictConfig

from llmass.modes import warmup, projects
from llmass.utils.common import get_config_path


CONFIG_NAME = "config_llm_runner"
LOGGER = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)


def llm_runner(cfg: DictConfig) -> None:
    instantiate(cfg.mode)(cfg)
    

if __name__ == "__main__":
    hydra.main(
        config_path=str(get_config_path()),
        config_name=CONFIG_NAME,
        version_base="1.3",
    )(llm_runner)()

