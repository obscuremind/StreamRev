import importlib
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any, List
from src.core.logging.logger import logger


@dataclass(frozen=True)
class ModuleManifest:
    name: str
    version: str
    compatibility: str = "streamrev-v1"


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
        self._manifests: Dict[str, ModuleManifest] = {}

    def discover(self) -> List[str]:
        found = []
        if not os.path.exists(self.modules_dir):
            return found
        for name in os.listdir(self.modules_dir):
            module_path = os.path.join(self.modules_dir, name)
            if os.path.isdir(module_path) and os.path.exists(os.path.join(module_path, "__init__.py")):
                found.append(name)
        return found

    def _validate_manifest(self, module_name: str, mod: Any, instance: ModuleInterface) -> ModuleManifest:
        raw = getattr(mod, "MODULE_MANIFEST", None)
        if isinstance(raw, dict) and raw.get("name") and raw.get("version"):
            return ModuleManifest(
                name=str(raw["name"]),
                version=str(raw["version"]),
                compatibility=str(raw.get("compatibility", "streamrev-v1")),
            )

        logger.warning("Module '%s' has no MODULE_MANIFEST; inferring from interface methods", module_name)
        return ModuleManifest(name=instance.get_name(), version=instance.get_version())

    def load(self, module_name: str) -> Optional[ModuleInterface]:
        try:
            mod = importlib.import_module(f"src.modules.{module_name}")
            if hasattr(mod, "Module"):
                instance = mod.Module()
                manifest = self._validate_manifest(module_name, mod, instance)
                self._modules[module_name] = instance
                self._manifests[module_name] = manifest
                logger.info(
                    "Loaded module: %s v%s (%s)", manifest.name, manifest.version, manifest.compatibility
                )
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

    def get_manifest(self, name: str) -> Optional[ModuleManifest]:
        return self._manifests.get(name)

    def manifests(self) -> Dict[str, ModuleManifest]:
        return self._manifests
