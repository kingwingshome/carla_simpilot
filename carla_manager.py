import json
import os
import subprocess
import psutil
from typing import Optional, Sequence


class CarlaSimulatorManager:
    _instance: Optional["CarlaSimulatorManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = "carla_config.json") -> None:
        if getattr(self, "_initialized", False):
            return
        self._config_path = config_path
        self._carla_executable: Optional[str] = None
        self._language: str = "zh-CN"
        # self._process is kept for compatibility but logic relies on psutil
        self._process: Optional[subprocess.Popen] = None
        self._load_config()
        self.render_quality = "Epic" # Low/Epic
        self._initialized = True

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, lang: str) -> None:
        self._language = lang
        self._save_config()

    @property
    def carla_executable(self) -> Optional[str]:
        return self._carla_executable

    @carla_executable.setter
    def carla_executable(self, path: str) -> None:
        self.set_carla_executable(path, save=True)

    def set_carla_executable(self, path: str, save: bool = False) -> None:
        normalized = os.path.abspath(path)
        if not os.path.isfile(normalized):
            raise FileNotFoundError(normalized)
        self._carla_executable = normalized
        if save:
            self._save_config()

    def _find_carla_process(self) -> Optional[psutil.Process]:
        """查找名称包含 'CarlaUE4' 的进程"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # 宽松匹配，覆盖 CarlaUE4.exe 或 CARLA UE4 等变体
                if proc.info['name'] and "CarlaUE4" in proc.info['name']:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def start(self, args: Optional[Sequence[str]] = None, cwd: Optional[str] = None) -> None:
        # 启动前检查是否已有实例运行
        existing_process = self._find_carla_process()
        if existing_process:
            # 已经运行则不重复启动
            # 可以在这里打印日志或抛出提示，根据需求选择
            # 这里选择静默返回，视为“确保已启动”
            return

        if not self._carla_executable:
            raise RuntimeError("CARLA 可执行文件路径未配置")
            
        command = [self._carla_executable]
        if args:
            command.append(args)
        working_dir = cwd or os.path.dirname(self._carla_executable)
        print(f"启动CARLA命令: {' '.join(command)}")
        # 启动新进程
        self._process = subprocess.Popen(command, cwd=working_dir)
        # command = [self._carla_executable, f"-quality-level={self.render_quality}"]

    def stop(self, timeout: float = 10.0) -> None:
        # 查找所有相关进程并终止
        # 可能会有多个（虽然 start 限制了，但可能是外部启动的）
        found_any = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and "CarlaUE4" in proc.info['name']:
                    found_any = True
                    proc.terminate()
                    try:
                        proc.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        self._process = None

    def is_running(self) -> bool:
        return self._find_carla_process() is not None

    def _load_config(self) -> None:
        if not os.path.isfile(self._config_path):
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        path = data.get("carla_executable")
        if isinstance(path, str) and path:
            self._carla_executable = path
        
        lang = data.get("language")
        if isinstance(lang, str) and lang:
            self._language = lang

    def _save_config(self) -> None:
        data = {
            "carla_executable": self._carla_executable,
            "language": self._language
        }
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
