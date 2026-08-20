import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class UploadValidationResult:
    valid: bool
    errors: list[str]


class UploadSessionValidator:
    CONFIG_SUFFIXES = {
        ".yml",
        ".yaml",
        ".json",
    }

    WORKLOAD_PATH_FIELDS = {
        "kernel_file",
        "input_bin",
    }

    def validate(
            self,
            temp_path: str,
    ) -> UploadValidationResult:
        errors: list[str] = []

        temp_root = Path(
            temp_path
        ).resolve()

        chip_config_root = (
                temp_root / "chip_config"
        )

        workload_root = (
                temp_root / "workload"
        )

        self._validate_config_package(
            package_name="chip_config",
            package_root=chip_config_root,
            errors=errors,
        )

        workload_configs = (
            self._validate_config_package(
                package_name="workload",
                package_root=workload_root,
                errors=errors,
            )
        )

        for config_path in workload_configs:
            data = self._load_config(
                config_path,
                errors,
            )

            if data is None:
                continue

            self._validate_workload_paths(
                value=data,
                workload_root=workload_root,
                config_path=config_path,
                errors=errors,
            )

        return UploadValidationResult(
            valid=not errors,
            errors=errors,
        )

    def _validate_config_package(
            self,
            package_name: str,
            package_root: Path,
            errors: list[str],
    ) -> list[Path]:
        if not package_root.is_dir():
            errors.append(
                f"{package_name} directory does not exist"
            )
            return []

        config_files = sorted(
            path
            for path in package_root.rglob("*")
            if (
                    path.is_file()
                    and path.suffix.lower()
                    in self.CONFIG_SUFFIXES
            )
        )

        if not config_files:
            errors.append(
                f"{package_name} contains no YAML/JSON config files"
            )
            return []

        # chip_config 也在这里完成语法检查。
        if package_name == "chip_config":
            for config_path in config_files:
                self._load_config(
                    config_path,
                    errors,
                )

        return config_files

    def _load_config(
            self,
            config_path: Path,
            errors: list[str],
    ) -> Any | None:
        try:
            with config_path.open(
                    "r",
                    encoding="utf-8",
            ) as file:
                if (
                        config_path.suffix.lower()
                        == ".json"
                ):
                    return json.load(file)

                return yaml.safe_load(file)

        except Exception as exc:
            errors.append(
                f"Invalid config file "
                f"{config_path.name}: {exc}"
            )

            return None

    def _validate_workload_paths(
            self,
            value: Any,
            workload_root: Path,
            config_path: Path,
            errors: list[str],
    ) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if (
                        key
                        in self.WORKLOAD_PATH_FIELDS
                ):
                    self._validate_asset_path(
                        field_name=key,
                        field_value=child,
                        workload_root=workload_root,
                        config_path=config_path,
                        errors=errors,
                    )
                else:
                    self._validate_workload_paths(
                        value=child,
                        workload_root=workload_root,
                        config_path=config_path,
                        errors=errors,
                    )

        elif isinstance(value, list):
            for child in value:
                self._validate_workload_paths(
                    value=child,
                    workload_root=workload_root,
                    config_path=config_path,
                    errors=errors,
                )

    def _validate_asset_path(
            self,
            field_name: str,
            field_value: Any,
            workload_root: Path,
            config_path: Path,
            errors: list[str],
    ) -> None:
        if not isinstance(
                field_value,
                str,
        ):
            errors.append(
                f"{config_path.name}: "
                f"{field_name} must be a string"
            )
            return

        asset_path = Path(
            field_value
        )

        if asset_path.is_absolute():
            errors.append(
                f"{config_path.name}: "
                f"{field_name} must use a "
                f"relative path: {field_value}"
            )
            return

        resolved_path = (
                workload_root
                / asset_path
        ).resolve()

        workload_root_resolved = (
            workload_root.resolve()
        )

        try:
            resolved_path.relative_to(
                workload_root_resolved
            )
        except ValueError:
            errors.append(
                f"{config_path.name}: "
                f"{field_name} escapes workload "
                f"directory: {field_value}"
            )
            return

        if not resolved_path.is_file():
            errors.append(
                f"{config_path.name}: "
                f"{field_name} file not found: "
                f"{field_value}"
            )