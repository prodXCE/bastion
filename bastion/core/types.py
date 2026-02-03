import uuid
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional

class JobStatus(Enum):
    """
    this enum defines every possible state a build job can be in.
    """
    PENDING = auto()
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    ERROR = auto()


@dataclass
class Job:
    """
    holds all info about a single build request
    """
    name: str
    commands: List[str]
    artifacts: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    log_path: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0

    # Helper Methods (state transitions)
    def state(self):
        """
        transitios the job to the RUNNING state
        records the exacts time is stated.
        """
        self.status = JobStatus.RUNNING
        self.start_time = time.time()

    def complete(self, success: bool)
        """
        transitions the job to a terminal state (SUCCESS or FAILED)
        records the exact time it finished.
        """
        if success:
            self.status = JobStatus.SUCCESS
        else:
            self.status = JobStatus.FAILED

        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """
        calculates how many seconds the job ran.
        """
        if self.end_time == 0.0:
            return 0.0
        return self.end_time - self.start_time
