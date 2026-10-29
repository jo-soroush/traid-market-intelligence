"""F2 retries and SDK send limits through the real pinned botocore, with a fake HTTP transport registered
on ``before-send`` (no socket is ever opened: the offline fixture refuses connections)."""
import json

import botocore
import botocore.exceptions as E
from botocore.awsrequest import AWSResponse
from botocore.config import Config
import pytest

from ai_support import T, T1, FakeClock, FakeProvider, failure, market_state, offline, record_root, valid_output  # noqa: F401
from traid.ai import AIService, AIStatus, EvidenceInputs, ProcessSlot, RecordStore, select
from traid.ai.bedrock import DEFAULT_MODEL_ID, BedrockConverseProvider, SEND_EVENT
from traid.ai.prompts import TOOL_NAME

INPUTS = EvidenceInputs(market_state=market_state())
SEL = select(T1, T, INPUTS)
REQUEST = json.loads(SEL.request_json)


class Raw:
    def __init__(self, body: bytes):
        self._body = body

    def stream(self, **kwargs):
        yield self._body

    def read(self, *args, **kwargs):
        return self._body


def ok_body(tool_input=None, stop="tool_use"):
    return json.dumps({"output": {"message": {"role": "assistant", "content": [
        {"toolUse": {"toolUseId": "tool-1", "name": TOOL_NAME, "input": tool_input or valid_output(REQUEST)}}]}},
        "stopReason": stop, "usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
        "metrics": {"latencyMs": 7}}).encode()


def http(status, error_type=None, body=None):
    return ("http", status, error_type, body)


class Transport:
    """A scripted HTTP layer: each entry is ``http(...)`` or an exception raised at send time."""
    def __init__(self, script, *, retries=None):
        self.script = list(script)
        self.requests = []
        self.retries = retries

    def install(self, provider: BedrockConverseProvider):
        def make(credentials, connect_timeout, read_timeout):
            if self.retries is not None:      # only to force an SDK-internal retry (RT-5)
                import boto3
                key, secret, token = credentials
                client = boto3.client("bedrock-runtime", region_name=provider.source_region, aws_access_key_id=key,
                                      aws_secret_access_key=secret, aws_session_token=token,
                                      config=Config(retries=self.retries, connect_timeout=connect_timeout,
                                                    read_timeout=read_timeout))
            else:
                client = provider._default_client(credentials, connect_timeout, read_timeout)
            self.config = client.meta.config
            client.meta.events.register_last(SEND_EVENT, self.respond)
            return client
        provider._client_factory = make
        return provider

    def respond(self, request, **kwargs):
        self.requests.append(request)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        _, status, error_type, body = item
        headers = {"x-amzn-RequestId": f"rid-{len(self.requests)}", "Content-Type": "application/json"}
        if error_type:
            headers["x-amzn-ErrorType"] = error_type
            body = body or json.dumps({"message": "scripted"}).encode()
        return AWSResponse(request.url, status, headers, Raw(body or ok_body()))


def provider(transport, *, verified=frozenset(), resolver=None):
    calls = []

    def creds():
        calls.append(1)
        if resolver:
            return resolver()
        return ("TESTKEYID", "test-secret", None)
    p = BedrockConverseProvider(source_region="eu-north-1", verified_retry_assumptions=verified,
                                credentials_resolver=creds)
    p.credential_calls = calls
    return transport.install(p)


def run(p, record_root, clock=None):
    svc = AIService(p, RecordStore(record_root), clock=clock or FakeClock(), slot=ProcessSlot())
    return svc.interpret(T1, T, INPUTS), svc


def attempts(result):
    from traid.ai import load_record
    return load_record(result.record_path).attempts


def test_rt0_before_send_short_circuits_http_and_the_request_is_the_approved_converse_shape(record_root):
    t = Transport([http(200)])
    result, _ = run(provider(t), record_root)
    assert result.status is AIStatus.VALID and len(t.requests) == 1
    req = t.requests[0]
    assert req.url == "https://bedrock-runtime.eu-north-1.amazonaws.com/model/eu.amazon.nova-pro-v1%3A0/converse"
    assert DEFAULT_MODEL_ID == "eu.amazon.nova-pro-v1:0"
    body = json.loads(req.body)
    assert set(body) == {"system", "messages", "inferenceConfig", "toolConfig"}
    assert body["inferenceConfig"] == {"maxTokens": 2000, "temperature": 0.0}
    assert body["toolConfig"]["toolChoice"] == {"tool": {"name": TOOL_NAME}}
    assert [m["role"] for m in body["messages"]] == ["user"] and body["messages"][0]["content"][0]["text"] == SEL.request_json
    assert t.config.retries == {"total_max_attempts": 1, "mode": "standard"} and t.config.max_pool_connections == 1
    (a,) = attempts(result)
    assert (a.http_sends, a.request_id, a.input_tokens, a.provider_latency_ms, a.stop_reason) == (1, "rid-1", 100, 7, "tool_use")


ROWS = [
    (E.ConnectTimeoutError(endpoint_url="https://x"), "ENDPOINT_UNREACHABLE", "U-R1"),
    (E.EndpointConnectionError(endpoint_url="https://x"), "ENDPOINT_UNREACHABLE", "U-R1"),
    (E.ProxyConnectionError(proxy_url="https://p", error="refused"), "PROXY_CONNECTION_FAILED", None),
    (E.SSLError(endpoint_url="https://x", error="handshake"), "REMOTE_OUTCOME_UNKNOWN", None),
    (E.ReadTimeoutError(endpoint_url="https://x"), "REMOTE_OUTCOME_UNKNOWN", None),
    (E.ConnectionClosedError(endpoint_url="https://x"), "REMOTE_OUTCOME_UNKNOWN", None),
    (RuntimeError("anything else during SEND"), "REMOTE_OUTCOME_UNKNOWN", None),
    (http(429, "ThrottlingException"), "PROVIDER_THROTTLED", "U-R2"),
    (http(400, "ThrottlingException"), "PROVIDER_THROTTLED", "U-R2"),          # classified by code, not HTTP status
    (http(429, "ModelNotReadyException"), "MODEL_NOT_READY", "U-R2"),
    (http(503, "ServiceUnavailableException"), "PROVIDER_ERROR", None),
    (http(500, "InternalServerException"), "PROVIDER_ERROR", None),
    (http(408, "ModelTimeoutException"), "PROVIDER_ERROR", None),
    (http(424, "ModelErrorException"), "PROVIDER_ERROR", None),
    (http(400, "ValidationException"), "PROVIDER_REJECTED_REQUEST", None),
    (http(403, "AccessDeniedException"), "PROVIDER_REJECTED_REQUEST", None),
    (http(404, "ResourceNotFoundException"), "PROVIDER_REJECTED_REQUEST", None),
    (http(400, "ServiceQuotaExceededException"), "PROVIDER_REJECTED_REQUEST", None),
    (http(400, "SomethingNewException"), "PROVIDER_REJECTED_REQUEST", None),
]


@pytest.mark.parametrize("item,expected,assumption", ROWS)
def test_rt1_classification_table_and_unverified_assumptions_fail_closed(record_root, item, expected, assumption):
    # unverified (the default): never retried, one send
    t = Transport([item])
    result, _ = run(provider(t), record_root)
    assert (result.status, result.reasons) == (AIStatus.AI_UNAVAILABLE, (expected,))
    assert len(t.requests) == 1 and [(a.http_sends, a.retry_safe) for a in attempts(result)] == [(1, False)]
    if assumption:
        # recorded as verified by the owner: retried once, two sends in total, each counted
        t = Transport([item, http(200)])
        result, _ = run(provider(t, verified=frozenset({assumption})), record_root)
        assert result.status is AIStatus.VALID and len(t.requests) == 2
        assert [(a.number, a.http_sends) for a in attempts(result)] == [(1, 1), (2, 1)]


def test_rt2_unknown_remote_outcome_is_never_retried_even_when_everything_is_verified(record_root):
    for error in (E.ReadTimeoutError(endpoint_url="https://x"), E.ConnectionClosedError(endpoint_url="https://x")):
        t = Transport([error, http(200)])
        result, _ = run(provider(t, verified=frozenset({"U-R1", "U-R2"})), record_root)
        assert result.reasons == ("REMOTE_OUTCOME_UNKNOWN",) and len(t.requests) == 1


def test_rt3_at_most_two_attempts_and_credentials_resolved_once(record_root):
    t = Transport([http(429, "ThrottlingException"), http(429, "ThrottlingException"), http(200)])
    p = provider(t, verified=frozenset({"U-R2"}))
    result, _ = run(p, record_root)
    assert result.reasons == ("PROVIDER_THROTTLED",) and len(t.requests) == 2 and len(p.credential_calls) == 1


def test_rt4_environment_retry_settings_cannot_add_sends(record_root, monkeypatch):
    monkeypatch.setenv("AWS_MAX_ATTEMPTS", "10")
    monkeypatch.setenv("AWS_RETRY_MODE", "adaptive")
    t = Transport([http(503, "ServiceUnavailableException")] * 10)
    result, _ = run(provider(t), record_root)
    assert result.reasons == ("PROVIDER_ERROR",) and len(t.requests) == 1


def test_rt5_a_forced_sdk_retry_is_blocked_by_the_send_guard(record_root):
    t = Transport([http(503, "ServiceUnavailableException")] * 3, retries={"total_max_attempts": 3, "mode": "standard"})
    result, _ = run(provider(t), record_root)
    assert result.reasons == ("SDK_RETRY_BLOCKED",) and len(t.requests) == 1
    assert [a.http_sends for a in attempts(result)] == [1]


@pytest.mark.parametrize("stop,expected", [("content_filtered", "CONTENT_FILTERED"), ("max_tokens", "OUTPUT_TRUNCATED"),
                                           ("guardrail_intervened", "CONTENT_FILTERED")])
def test_rt6_invalid_output_is_never_retried(record_root, stop, expected):
    t = Transport([http(200, body=ok_body(stop=stop)), http(200)])
    result, _ = run(provider(t, verified=frozenset({"U-R1", "U-R2"})), record_root)
    assert (result.status, result.reasons) == (AIStatus.AI_INVALID, (expected,)) and len(t.requests) == 1
    t = Transport([http(200, body=json.dumps({"output": {"message": {"role": "assistant", "content": [
        {"toolUse": {"toolUseId": "t", "name": TOOL_NAME, "input": {"summary": 1}}}]}}, "stopReason": "tool_use"}).encode())])
    result, _ = run(provider(t), record_root)
    assert result.reasons == ("SCHEMA_INVALID",) and len(t.requests) == 1


def test_rt7_no_retry_without_enough_time(record_root):
    clock = FakeClock()
    p = FakeProvider([lambda r: (clock.set(1000.0 + 39.0), failure("PROVIDER_THROTTLED", retry_safe=True))[1],
                      lambda r: valid_output(json.loads(r.user_text))])
    result, _ = run(p, record_root, clock)
    assert result.reasons == ("PROVIDER_THROTTLED",) and len(p.calls) == 1             # 39 + 2 + 20 > 65 - 5
    clock = FakeClock()
    p = FakeProvider([lambda r: (clock.set(1000.0 + 38.0), failure("PROVIDER_THROTTLED", retry_safe=True))[1],
                      lambda r: valid_output(json.loads(r.user_text))])
    result, _ = run(p, record_root, clock)
    assert result.status is AIStatus.VALID and len(p.calls) == 2
    assert p.calls[1][1] == 5.0 and p.calls[1][2] == 15.0                               # B = 65 - 5 - 40


def test_setup_and_construction_failures_send_nothing(record_root):
    t = Transport([http(200)])
    result, _ = run(provider(t, resolver=lambda: (_ for _ in ()).throw(E.NoCredentialsError())), record_root)
    assert result.reasons == ("CREDENTIALS_UNAVAILABLE",) and t.requests == []
    p = provider(Transport([http(200)]))
    real = p.converse_params
    p.converse_params = lambda request: {**real(request), "inferenceConfig": {"maxTokens": "2000"}}   # wrong type
    result, _ = run(p, record_root)
    assert result.reasons == ("REQUEST_CONSTRUCTION_FAILED",) and attempts(result)[0].http_sends == 0


def test_pinned_sdk_version():
    import boto3
    assert boto3.__version__ == botocore.__version__ == "1.43.121"
