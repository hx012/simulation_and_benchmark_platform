import re
from pathlib import Path


class SimulationResultParser:
    SIMULATED_TIME_PATTERN = re.compile(
        r"Simulation is complete,\s*"
        r"simulated time:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(ps|ns|us|ms|s)\b",
        re.IGNORECASE,
    )

    UNIT_TO_SECONDS = {
        "ps": 1e-12,
        "ns": 1e-9,
        "us": 1e-6,
        "ms": 1e-3,
        "s": 1.0,
    }

    def parse_simulated_time_seconds(
            self,
            text: str,
    ) -> float | None:
        matches = list(
            self.SIMULATED_TIME_PATTERN.finditer(text)
        )

        if not matches:
            return None

        match = matches[-1]

        value = float(match.group(1))
        unit = match.group(2).lower()

        return value * self.UNIT_TO_SECONDS[unit]

    def parse_simulated_time_from_file(
            self,
            log_path: Path,
            tail_bytes: int = 1024 * 1024,
    ) -> float | None:
        if not log_path.is_file():
            return None

        file_size = log_path.stat().st_size

        with log_path.open("rb") as file:
            file.seek(
                max(
                    0,
                    file_size - tail_bytes,
                    )
            )

            text = file.read().decode(
                "utf-8",
                errors="replace",
            )

        return self.parse_simulated_time_seconds(
            text
        )