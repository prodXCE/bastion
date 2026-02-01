import uuid
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional

class JobStatus(Enum):
    """
    Represents the status of a job in the CI system.
    """
    PENDING = auto()   # job created, waiting for resources
    PREPARING = auto() # system is setting up the Jail/Zfs
    RUNNING = auto()   # the user's script is executing
    SUCCESS = auto()   # the scriping finishes with exit code 0
    FAILED = auto()    # the script finished with exit code > 0
    ERROR = auto()     # the CI system itself crashed (infra failure)

@dataclass
class Job:
    """
    holds all info about a single build request.
    """

    name: str
    commands: List[str]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    log_path: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0

    # helper methods
    def start(self):
        """
        transitions the job to the `running` state.
        records the exact time it started.
        """
        self.status = JobStatus.RUNNING
        self.start_time = time.time()

    def complete(self, success: bool):
        """
        transitions the job to a terminal state (success or failed)
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
        calcs how many seconds the job ran
        """
        if self.end_time == 0.0:
            return 0.0
        return self.end_time - self.start_time
