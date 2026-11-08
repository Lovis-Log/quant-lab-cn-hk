"""Whitelisted screening recipes only; never store market responses."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
from threading import RLock
from uuid import uuid4
from quant_lab.paths import user_data_dir
from quant_lab.screening import ScreenRecipe

_lock = RLock()


class ScreenPresetStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else user_data_dir() / "screen-presets.json"

    def load(self):
        if not self.path.exists():
            return {}
        if self.path.stat().st_size > 65536:
            raise ValueError("筛选方案文件过大。")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if set(payload) != {"format", "recipes"} or payload["format"] != 1 or not isinstance(payload["recipes"], dict):
            raise ValueError("筛选方案格式不受支持。")
        recipes = {}
        for name, value in payload["recipes"].items():
            if not isinstance(name, str) or not name.strip() or len(name) > 80 or not isinstance(value, dict):
                raise ValueError("筛选方案名称或内容无效。")
            if set(value) != {"market", "codes", "adjustment", "bounds", "sort", "ascending"}:
                raise ValueError("筛选方案存在不受支持的字段。")
            recipe = ScreenRecipe(**{**value, "codes": tuple(value["codes"]), "bounds": tuple(tuple(v) for v in value["bounds"])})
            recipe.validate()
            recipes[name] = recipe
        return recipes

    def write(self, name, recipe=None, *, delete=False):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise ValueError("方案名称须为1–80个字符。")
        with _lock:
            recipes = self.load()  # A damaged old file must not be silently replaced.
            if delete:
                recipes.pop(name, None)
            else:
                recipe.validate()
                recipes[name.strip()] = recipe
            payload = json.dumps({"format": 1, "recipes": {key: asdict(value) for key, value in recipes.items()}}, ensure_ascii=False, indent=2)
            if len(payload.encode("utf-8")) > 65536:
                raise ValueError("方案总量超过64KB，请先删除部分方案。")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                shutil.copy2(self.path, self.path.with_suffix(".json.bak"))
            temporary = self.path.with_name(self.path.name + "." + uuid4().hex + ".tmp")
            try:
                temporary.write_text(payload, encoding="utf-8")
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
