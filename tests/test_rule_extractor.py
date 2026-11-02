from app.services.rule_extractor import RuleExtractor, detect_owner, strip_quoted


def extract(text, user="alice"):
    return RuleExtractor().extract([{"user": user, "text": text}])


def categories(text, user="alice"):
    return {item.category for item in extract(text, user)}


def test_explicit_blocker_is_detected():
    [item] = extract("We are blocked on the staging deploy.")
    assert item.category == "blocker"
    assert item.msg_index == 0
    assert item.speaker == "alice"
    assert item.confidence >= 0.85


def test_negated_blocker_is_not_detected():
    assert categories("The deploy is not blocked anymore.") == set()


def test_no_longer_blocked_is_not_detected():
    assert categories("We are no longer blocked on infra.") == set()


def test_attributed_quote_is_not_detected():
    assert categories('Alice said: "the API is blocked" but it is fine now.') == set()


def test_blockquote_is_not_detected():
    assert categories("> we are blocked on infra\nUpdate: infra is healthy.") == set()


def test_inline_code_is_not_detected():
    assert categories("The alert said `500 Internal Server Error` from the load test.") == set()


def test_unblocked_is_not_a_blocker():
    assert categories("The payments integration is unblocked now.") == set()


def test_resolved_bug_is_not_detected():
    assert categories("The auth crash is fixed and deployed.") == set()


def test_decision_survives_negation():
    found = extract("We decided not to ship on Friday.")
    assert [item.category for item in found] == ["decision"]


def test_question_action_item_has_lower_confidence():
    [item] = extract("Can someone review PR #482?")
    assert item.category == "action_item"
    assert item.confidence < 0.8


def test_owner_from_mention():
    [item] = extract("Can someone review PR #482? @priya please take a look.", user="erin")
    assert item.owner == "priya"


def test_owner_from_assignment():
    [item] = extract("Action item: migrate the analytics job - assigned to Priya.")
    assert item.category == "action_item"
    assert item.owner == "priya"


def test_owner_from_named_actor():
    [item] = extract("Marcus will update the runbook by Thursday.", user="frank")
    assert item.owner == "marcus"


def test_owner_falls_back_to_speaker_for_first_person():
    [item] = extract("I'll rotate the API keys after standup.", user="alice")
    assert item.owner == "alice"


def test_one_item_per_message_and_category():
    found = extract(
        "Blocked by the API key rotation. The rotation is blocking the deploy. "
        "Also blocked on the cert."
    )
    assert len(found) == 1


def test_speaker_can_be_missing():
    [item] = RuleExtractor().extract([{"text": "I'll handle it."}])
    assert item.speaker is None
    assert item.owner is None


def test_messages_without_text_are_skipped():
    assert RuleExtractor().extract([{"user": "alice"}, {"user": "bob", "text": "   "}]) == []


def test_strip_quoted_removes_blockquotes_and_code():
    cleaned = strip_quoted("> quoted\nReal line `code`")
    assert "quoted" not in cleaned
    assert "code" not in cleaned
    assert "Real line" in cleaned


def test_numeric_mention_is_a_known_false_positive():
    # Documented limitation: a bare number cannot be distinguished from a
    # message about 500 units. It is counted as a false positive in the eval.
    assert "bug" in categories("We shipped 500 units last quarter.")


def test_detect_owner_returns_none_without_signal():
    assert detect_owner("The deploy finished on time.", "alice") is None
