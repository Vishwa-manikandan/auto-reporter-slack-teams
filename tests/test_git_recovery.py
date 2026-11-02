from app.services.git_recovery_service import GitRecoveryService


def test_inspect_repository_state():
    svc = GitRecoveryService()
    state = svc.inspect_repository_state()
    assert "has_git" in state


def test_classify_failure():
    svc = GitRecoveryService()
    assert svc.classify_failure("Could not resolve host") == "NETWORK"
    assert svc.classify_failure("Permission denied") == "AUTH"
    assert svc.classify_failure("non-fast-forward") == "DIVERGENT"
