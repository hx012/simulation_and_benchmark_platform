import json
import shutil
from pathlib import Path
from typing import Any

import yaml


class WorkloadResolveError(Exception):
    pass


class WorkloadConfigResolver:
    """
    Convert user workload config into simulator-ready config.

    Original input:
        <workspace>/input/workload/

    Resolved config:
        <workspace>/runtime/resolved_config/workload/

    The original input is never modified.
    """

    PATH_FIELDS = {
        "kernel_file",
        "input_bin",
    }

    CONFIG_SUFFIXES = {
        ".yml",
        ".yaml",
        ".json",
    }

    TOP_CONFIG_NAME = "top.yml"

    def resolve(
        self,
        input_workload_dir: Path,
        resolved_workload_dir: Path,
    ) -> None:
        input_root = input_workload_dir.resolve()
        resolved_root = resolved_workload_dir.resolve()

        if not input_root.is_dir():
            raise WorkloadResolveError(
                f"Workload directory does not exist: "
                f"{input_root}"
            )

        # 每次 PREPARING 都重新生成，避免使用旧配置。
        if resolved_root.exists():
            shutil.rmtree(resolved_root)

        resolved_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        config_count = 0

        for source_path in input_root.rglob("*"):
            relative_path = source_path.relative_to(
                input_root
            )

            target_path = (
                resolved_root / relative_path
            )

            if source_path.is_dir():
                target_path.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                continue

            if (
                source_path.suffix.lower()
                not in self.CONFIG_SUFFIXES
            ):
                # .o / .bin 等资产仍保留在 input/workload，
                # 不复制到 resolved_config。
                continue

            target_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            data = self._load_config(
                source_path
            )

            if source_path.name == self.TOP_CONFIG_NAME:
                data = self._resolve_top_config(
                    data=data,
                    input_root=input_root,
                    resolved_root=resolved_root,
                )
            else:
                data = self._resolve_path_fields(
                    node=data,
                    input_root=input_root,
                )

            self._write_config(
                target_path,
                data,
            )

            config_count += 1

        if config_count == 0:
            raise WorkloadResolveError(
                f"No workload config files found in: "
                f"{input_root}"
            )

    def _resolve_path_fields(
        self,
        node: Any,
        input_root: Path,
    ) -> Any:
        if isinstance(node, dict):
            result = {}

            for key, value in node.items():
                if (
                    key in self.PATH_FIELDS
                    and isinstance(value, str)
                    and value
                ):
                    result[key] = str(
                        self._resolve_asset_path(
                            value,
                            input_root,
                        )
                    )
                else:
                    result[key] = (
                        self._resolve_path_fields(
                            value,
                            input_root,
                        )
                    )

            return result

        if isinstance(node, list):
            return [
                self._resolve_path_fields(
                    item,
                    input_root,
                )
                for item in node
            ]

        return node

    def _resolve_asset_path(
        self,
        value: str,
        input_root: Path,
    ) -> Path:
        path = Path(value)

        # 平台输入规范：
        # 用户只能填写相对于 Workload Package 根目录的路径。
        if path.is_absolute():
            raise WorkloadResolveError(
                f"Absolute workload asset path is not allowed: "
                f"{value}"
            )

        resolved_path = (
            input_root / path
        ).resolve()

        if not resolved_path.is_relative_to(input_root):
            raise WorkloadResolveError(
                f"Workload asset escapes package root: "
                f"{value}"
            )

        if not resolved_path.is_file():
            raise WorkloadResolveError(
                f"Workload asset does not exist: "
                f"{value} "
                f"(resolved to {resolved_path})"
            )

        return resolved_path

    def _resolve_top_config(
        self,
        data: Any,
        input_root: Path,
        resolved_root: Path,
    ) -> Any:
        if not isinstance(data, dict):
            raise WorkloadResolveError(
                "top.yml must contain a mapping"
            )

        result = {}

        for chip_id, case_path_value in data.items():
            if not isinstance(
                case_path_value,
                str,
            ):
                raise WorkloadResolveError(
                    f"Invalid case path for "
                    f"{chip_id}: {case_path_value}"
                )

            case_path = Path(
                case_path_value
            )

            if case_path.is_absolute():
                raise WorkloadResolveError(
                    f"Absolute case path is not allowed: "
                    f"{case_path_value}"
                )

            source_case_dir = (
                input_root / case_path
            ).resolve()

            if not source_case_dir.is_relative_to(
                input_root
            ):
                raise WorkloadResolveError(
                    f"Case path escapes workload root: "
                    f"{case_path_value}"
                )

            if not source_case_dir.is_dir():
                raise WorkloadResolveError(
                    f"Case directory does not exist: "
                    f"{case_path_value}"
                )

            resolved_case_dir = (
                resolved_root / case_path
            ).resolve()

            if not resolved_case_dir.is_relative_to(
                resolved_root
            ):
                raise WorkloadResolveError(
                    f"Resolved case path escapes root: "
                    f"{case_path_value}"
                )

            result[chip_id] = str(
                resolved_case_dir
            )

        return result

    @staticmethod
    def _load_config(
        path: Path,
    ) -> Any:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            if path.suffix.lower() == ".json":
                return json.load(file)

            return yaml.safe_load(file)

    @staticmethod
    def _write_config(
        path: Path,
        data: Any,
    ) -> None:
        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            if path.suffix.lower() == ".json":
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                return

            yaml.safe_dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False,
            )
