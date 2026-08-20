import re


class CycleParser:
    """
    Parse SST global simulation cycle.

    Example:
        [Sim: 1608548(cycle)]
    """

    SIM_PATTERN = re.compile(
        r"\[Sim:\s*(\d+)\(cycle\)\]",
        re.IGNORECASE,
    )

    def parse_latest_cycle(
            self,
            text: str,
    ) -> int | None:
        matches = self.SIM_PATTERN.findall(text)

        if not matches:
            return None

        return max(int(cycle) for cycle in matches)