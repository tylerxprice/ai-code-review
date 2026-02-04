import subprocess
from unittest.mock import patch

import pytest

from ai_review.git_ops import GitOps


def test_git_ops_run_raises_runtime_error():
    git = GitOps(repo_path=".")
    err = subprocess.CalledProcessError(1, ["git", "status"], stderr="boom")
    with patch("ai_review.git_ops.subprocess.run", side_effect=err):
        with pytest.raises(RuntimeError) as exc:
            git._run(["status"])
    assert "boom" in str(exc.value)
