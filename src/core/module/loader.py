import importlib
import os
from typing import Dict, Optional, Any, List
from src.core.logging.logger import logger


class ModuleInterface:
    def get_name(self) -> str:
        raise NotImplementedError
    def get_version(self) -> str:
        raise NotImplementedError
    def boot(self, app: Any) -> None:
        pass
    def register_routes(self, router: Any) -> None:
        pass
    def get_event_subscribers(self) -> dict:
        return {}
    def install(self) -> None:
        pass
    def uninstall(self) -> None:
        pass


class ModuleLoader:
    def __init__(self, modules_dir: str):
        self.modules_dir = modules_dir
        self._modules: Dict[str, ModuleInterface] = {}

    def discover(self) -> List[str]:
        found = []
        if not os.path.exists(self.modules_dir):
            return found
        for name in os.listdir(self.modules_dir):
            module_path = os.path.join(self.modules_dir, name)
            if os.path.isdir(module_path) and os.path.exists(os.path.join(module_path, "__init__.py")):
                found.append(name)
        return found

    def load(self, module_name: str) -> Optional[ModuleInterface]:
        try:
            mod = importlib.import_module(f"src.modules.{module_name}")
            if hasattr(mod, "Module"):
                instance = mod.Module()
                self._modules[module_name] = instance
                logger.info(f"Loaded module: {module_name} v{instance.get_version()}")
                return instance
        except Exception as e:
            logger.error(f"Failed to load module '{module_name}': {e}")
        return None

    def load_all(self) -> Dict[str, ModuleInterface]:
        for name in self.discover():
            self.load(name)
        return self._modules

    def get_module(self, name: str) -> Optional[ModuleInterface]:
        return self._modules.get(name)

    def get_all(self) -> Dict[str, ModuleInterface]:
        return self._modules
