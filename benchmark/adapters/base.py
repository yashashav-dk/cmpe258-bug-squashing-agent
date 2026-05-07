from abc import ABC, abstractmethod
from typing import List

from benchmark.manifest import BenchmarkCase


class SourceAdapter(ABC):
    @abstractmethod
    def build_cases(self) -> List[BenchmarkCase]:
        """Build benchmark cases from a source strategy."""
