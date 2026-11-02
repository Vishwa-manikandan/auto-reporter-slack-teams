from eval.run_eval import evaluate, load_cases


def test_eval_set_is_labelled():
    cases = load_cases()
    assert len(cases) == 25
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        assert case["messages"], case["id"]
        for category, indices in case.get("expected", {}).items():
            for index in indices:
                assert 0 <= index < len(case["messages"]), case["id"]


def test_eval_meets_the_documented_floors():
    result = evaluate(load_cases())
    assert result["micro"]["precision"] >= 0.85
    assert result["micro"]["recall"] >= 0.60
    assert result["owners"]["accuracy"] >= 0.80


def test_eval_reports_known_failures_instead_of_hiding_them():
    result = evaluate(load_cases())
    failing = {failure["case"] for failure in result["failures"]}
    # These are documented limitations, not regressions. If the extractor starts
    # handling them the eval numbers improve and this assertion should change.
    assert "hard-implicit-blocker" in failing
    assert "numeric-false-positive" in failing
