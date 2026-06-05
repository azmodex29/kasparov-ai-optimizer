import time
from datetime import datetime


class PipelineLogger:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.steps = []
        self.start_time = time.time()

    def log(self, step: str, status: str, detail: str = ""):
        elapsed = round(time.time() - self.start_time, 2)
        entry = {
            "step": step,
            "status": status,
            "detail": detail,
            "elapsed_s": elapsed,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.steps.append(entry)
        print(f"[{self.run_id[:8]}] {elapsed}s | {step} | {status} | {detail}")

    def summary(self) -> dict:
        total = round(time.time() - self.start_time, 2)
        failed = [s for s in self.steps if s["status"] == "error"]
        return {
            "run_id": self.run_id,
            "total_time_s": total,
            "steps_completed": len(self.steps),
            "errors": len(failed),
            "log": self.steps
        }