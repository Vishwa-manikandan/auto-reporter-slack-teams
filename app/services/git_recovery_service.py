import subprocess
import time
from typing import Dict, Any, Optional


class GitRecoveryError(Exception):
    pass


class GitRecoveryService:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def _run(self, args, timeout=30):
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -2, "", str(e)

    def inspect_repository_state(self) -> Dict[str, Any]:
        rc, out, err = self._run(["rev-parse", "--git-dir"])
        return {"has_git": rc == 0, "git_dir": out.strip() if rc == 0 else None}

    def inspect_working_tree(self) -> Dict[str, Any]:
        rc, out, err = self._run(["status", "--porcelain"])
        return {"dirty": rc == 0 and bool(out.strip()), "changes": out.strip().splitlines() if rc == 0 else []}

    def inspect_branch_state(self) -> Dict[str, Any]:
        rc, out, err = self._run(["branch", "--show-current"])
        branch = out.strip() if rc == 0 else None
        rc2, out2, err2 = self._run(["rev-parse", "HEAD"])
        return {"branch": branch, "head": out2.strip() if rc2 == 0 else None}

    def classify_failure(self, error: str) -> str:
        e = error.lower()
        if "could not resolve host" in e or "timeout" in e or "connection" in e:
            return "NETWORK"
        if "authentication" in e or "permission denied" in e or "403" in e or "401" in e:
            return "AUTH"
        if "non-fast-forward" in e or "divergent" in e:
            return "DIVERGENT"
        if "conflict" in e:
            return "CONFLICT"
        return "UNKNOWN"

    def retry_operation(self, func, max_attempts=3, backoff=1):
        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts:
                    raise
                time.sleep(backoff * attempt)
        return None

    def generate_recovery_report(self, operation: str, error: str, action: str, result: str) -> Dict[str, Any]:
        return {
            "operation": operation,
            "original_error": error,
            "classification": self.classify_failure(error),
            "recovery_action": action,
            "result": result,
            "branch": self.inspect_branch_state().get("branch"),
        }
