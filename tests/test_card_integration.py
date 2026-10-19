"""Real Git histories and production checks; external GitHub responses are test fixtures."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from test_maintenance_harness import ROOT, consistency as c

ANCHOR = "b86a265e644bbac0674aad091769c38389ca7385"
SOURCE = "d26b45a3be831850ea8a8ac12b6d346d2ecad159"
BASE = "82eb0644b1e9912cd1dc972c646b489f26d081c4"
BRANCH = "fix/card-integration-lifecycle-c07"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "synthetic test", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
       "GIT_COMMITTER_NAME": "synthetic test", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, env=ENV, text=True).strip()


def field(repo, name, value):
    p = repo / "PROJECT_CONTROL.md"
    s = p.read_text()
    start = s.index("Card Integration Record:\n")
    end = s.index("\n```", s.index("```text", start))
    block, count = re.subn(rf"^{re.escape(name)}:.*$", name + ": " + value, s[start:end], flags=re.M)
    assert count == 1, name
    p.write_text(s[:start] + block + s[end:])


def freeze(repo):
    digest = c.worktree_candidate_identity(repo, ANCHOR, recorded_branch=BRANCH)["Candidate Diff SHA-256"]
    field(repo, "Correction Diff SHA-256", digest)
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    text = p.read_text()
    if "## 26. Card Integration Lifecycle Correction" in text:
        start = text.index("## 26. Card Integration Lifecycle Correction")
        tail = re.sub(r"^- Candidate Diff SHA-256:.*$", "- Candidate Diff SHA-256: " + digest, text[start:], flags=re.M)
        p.write_text(text[:start] + tail)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    subprocess.run(["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(r)], check=True)
    git(r, "checkout", "-B", "main", ANCHOR)
    # Own this synthetic scenario: never inherit the live project's current
    # Card/state/approval record (which will legitimately change on C08+).
    allowed = [".github/workflows/ci.yml", "scripts/harness_consistency_check.py", "scripts/check_maintenance_integration.py",
               "tests/test_card_integration.py", "tests/test_maintenance_harness.py",
               "GIT_WORKFLOW.md", "TRAID_ENGINEERING_HARNESS.md", "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"]
    for name in allowed:
        if name in {"PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"}:
            continue
        source = ROOT / name
        if source.exists():
            (r / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, r / name)
    p = r / "PROJECT_CONTROL.md"; text=p.read_text()
    start=text.index("Current active-Card record:");end=text.index("Current active-Card Contract/Risk Map:",start)
    block=text[start:end].replace("Human Delivery Approval: NOT_GRANTED", "Human Delivery Approval: GRANTED — synthetic test approval only")
    text=text[:start]+block+text[end:]
    text=text.replace("V1-C07 Authorization: START_GRANTED; DELIVERY_NOT_GRANTED", "V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_NOT_VERIFIED",1)
    values={"Card ID":"V1-C07", "Source Branch":"card/v1-c07-order-book-liquidity", "Base SHA":BASE,
            "Source Commit":SOURCE, "Merge Anchor":ANCHOR, "PR":"15",
            "Protected Paths":"src/traid/liquidity/__init__.py, src/traid/liquidity/analytics.py, tests/test_liquidity.py",
            "Integrated Paths":"PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, src/traid/liquidity/__init__.py, src/traid/liquidity/analytics.py, tests/test_harness_consistency.py, tests/test_liquidity.py, tests/test_maintenance_harness.py",
            "Human Merge Approval":"GRANTED — synthetic fixture only", "Post-Merge Verification":"NOT_VERIFIED", "Closure Approval":"NOT_GRANTED",
            "Correction Branch":BRANCH, "Correction Base SHA":ANCHOR, "Correction Paths":", ".join(allowed),
            "Correction Authorization":"GRANTED — synthetic local scope only", "Correction Diff SHA-256":"PENDING"}
    record="Card Integration Record:\n\n```text\n"+"".join(k+": "+v+"\n" for k,v in values.items())+"```\n\n"
    p.write_text(text.replace("Current active-Card Contract/Risk Map:",record+"Current active-Card Contract/Risk Map:",1))
    p=r/"TRAID_CARD_EVIDENCE_MAP.md";text=p.read_text()
    audit="""## 26. Card Integration Lifecycle Correction

Synthetic correction test evidence only; no real review or authorization.

### Independent Audit

- Status: PASS
- Candidate Type: WORKTREE
- Branch: fix/card-integration-lifecycle-c07
- Base SHA: b86a265e644bbac0674aad091769c38389ca7385
- Candidate Diff SHA-256: PENDING
- Untracked Files: tests/test_card_integration.py
- Verifier context: synthetic independent review fixture, not real approval
- Canonical inputs reviewed: synthetic correction contract
- Evidence reviewed: synthetic acceptance results
- Findings: NONE
- Unresolved blockers: NONE
- Gap dispositions: NONE
- Limitations: synthetic test only, no real delivery
- Verdict: PASS — synthetic fixture only
- Delivery authorization/performance: GRANTED / NOT_PERFORMED — MERGE_GRANTED; synthetic fixture only

"""
    p.write_text(text.replace("# 20. Final Evidence Principle",audit+"# 20. Final Evidence Principle",1))
    freeze(r)
    return r


def check(repo, monkeypatch, branch="main", *, verify_external=False):
    # Mock only the external GitHub observation, never local proof/authorization.
    monkeypatch.setattr(c, "github_card_merge_issues", lambda *args: ())
    return c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                    (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, branch, verify_external=verify_external)


def integrate_correction(repo):
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "synthetic authorized correction, not real approval")
    git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
    if (subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/" + BRANCH], cwd=repo).returncode
            or git(repo, "rev-parse", "refs/remotes/origin/" + BRANCH) == ANCHOR):
        git(repo, "update-ref", "refs/remotes/origin/" + BRANCH, git(repo, "rev-parse", "HEAD"))


def test_c07_recovery_and_authorized_later_tree(repo, monkeypatch):
    before = (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_bytes()
    assert check(repo, monkeypatch, BRANCH) == (True, ())
    integrate_correction(repo)
    assert check(repo, monkeypatch) == (True, ())
    assert (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_bytes() == before
    assert "V1-C07" not in c.completed_card_ids((repo / "PROJECT_CONTROL.md").read_text())
    assert c.committed_candidate_digest(repo, SOURCE, BASE, "card/v1-c07-order-book-liquidity") == "433d000025974a91a19763b7c296abed77657543516fa5c901550ec33cc17e76"


@pytest.mark.parametrize("name,value,reason", [
    ("Card ID", "V1-C08", "CARD_INTEGRATION_CARD_STATE_MISMATCH"),
    ("Source Branch", "card/v1-c08-wrong", "CARD_INTEGRATION_SOURCE_BRANCH_INVALID"),
    ("Base SHA", ANCHOR, "CARD_INTEGRATION_SOURCE_ANCESTRY_INVALID"),
    ("Source Commit", BASE, "CARD_INTEGRATION_SOURCE_ANCESTRY_INVALID"),
    ("Source Commit", ANCHOR, "CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH"),
    ("Merge Anchor", SOURCE, "CARD_INTEGRATION_ANCHOR_NOT_ANCESTOR"),
    ("Human Merge Approval", "NOT_GRANTED", "CARD_INTEGRATION_APPROVAL_MISSING"),
    ("Post-Merge Verification", "PASS", "CARD_INTEGRATION_CLOSURE_REQUIRES_RECORDED_TRANSITION"),
    ("Post-Merge Verification", "FAIL", "CARD_INTEGRATION_CLOSURE_REQUIRES_RECORDED_TRANSITION"),
    ("Correction Authorization", "NOT_GRANTED", "CARD_INTEGRATION_UNAUTHORIZED_SUBSEQUENT_CHANGE"),
    ("Correction Diff SHA-256", "0" * 64, "CARD_INTEGRATION_CORRECTION_DIGEST_MISMATCH"),
    ("Integrated Paths", "PROJECT_CONTROL.md", "CARD_INTEGRATION_SCOPE_INVALID"),
])
def test_invalid_bindings(repo, monkeypatch, name, value, reason):
    field(repo, name, value)
    freeze(repo) if name != "Correction Diff SHA-256" else None
    if name == "Source Commit" and value == ANCHOR:
        # Same tree isn't proof of the approved source commit: require real PR match.
        monkeypatch.setattr(c, "github_card_merge_issues", lambda *args: (reason,))
        result = c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(), (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, BRANCH, verify_external=True)
    else:
        result = check(repo, monkeypatch, BRANCH, verify_external=name == "Human Merge Approval")
    assert result == (False, (reason,))


@pytest.mark.parametrize("mutation", ["content", "mode", "symlink"])
def test_protected_bytes_modes_and_path_identity(repo, monkeypatch, mutation):
    p = repo / "src/traid/liquidity/analytics.py"
    if mutation == "content":
        p.write_text(p.read_text() + "\n# unauthorized\n")
    elif mutation == "mode":
        p.chmod(0o755)
    else:
        p.unlink()
        p.symlink_to("__init__.py")
    freeze(repo)
    assert check(repo, monkeypatch, BRANCH) == (False, ("CARD_INTEGRATION_PROTECTED_CONTENT_CHANGED",))


def test_unreviewed_added_file(repo, monkeypatch):
    (repo / "extra.py").write_text("unreviewed\n")
    freeze(repo)
    assert check(repo, monkeypatch, BRANCH) == (False, ("CARD_INTEGRATION_UNAUTHORIZED_SUBSEQUENT_CHANGE",))


def test_dirty_and_divergent_main(repo, monkeypatch):
    assert check(repo, monkeypatch) == (False, ("CARD_INTEGRATION_DIRTY_MAIN",))
    integrate_correction(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", ANCHOR)
    assert check(repo, monkeypatch) == (False, ("CARD_INTEGRATION_DIVERGENT_MAIN",))


@pytest.mark.parametrize("change", ["missing", "failed", "identity"])
def test_original_audit_is_immutable(repo, monkeypatch, change):
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    s = p.read_text(); start = s.index("### Independent Audit\n", s.index("## V1-C07 "))
    end = s.index("\n---", start)
    block = s[start:end]
    block = "" if change == "missing" else block.replace("- Status: PASS", "- Status: BLOCKED") if change == "failed" else block.replace("433d000", "0000000")
    p.write_text(s[:start] + block + s[end:]); freeze(repo)
    assert check(repo, monkeypatch, BRANCH) == (False, ("CARD_INTEGRATION_HISTORICAL_AUDIT_CHANGED",))


def test_main_production_path(repo):
    integrate_correction(repo)
    command = "import sys; sys.path.insert(0,'scripts'); import harness_consistency_check as m; raise SystemExit(m.main())"
    r = subprocess.run([sys.executable, "-c", command], cwd=repo, env={**ENV, "PYTHONPATH": str(repo / "src")}, text=True, capture_output=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "INTEGRATED_PENDING_VERIFICATION" in r.stdout and "CARD_COMPLETE: NO" in r.stdout


def test_source_validation_stays_strict(repo):
    assert c.active_card_candidate_issues((repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), c.CardRecord("V1-C07", "Order Book & Liquidity Analytics", "READY_FOR_HUMAN_REVIEW", True), repo, "main") == ("V1-C07:AUDITED_CANDIDATE_BRANCH_MISMATCH",)


def test_closure_needs_actual_verification(repo):
    assert c.github_card_closure_issues("NOT_VERIFIED", repo, ANCHOR) == ("CARD_CLOSURE_VERIFICATION_MISSING",)
    assert c.github_card_closure_issues("PASS — run:123 sha:" + "0" * 40 + " local:synthetic", repo, ANCHOR) == ("CARD_CLOSURE_VALIDATION_NOT_ANCESTOR",)


def future_candidate(repo, *, broken=False):
    """Hypothetical C08 governance fixture only; no C08 implementation/approval."""
    integrate_correction(repo)
    base = git(repo, "rev-parse", "HEAD")
    branch = "card/v1-c08-synthetic"
    git(repo, "switch", "-c", branch)
    p = repo / "PROJECT_CONTROL.md"
    s = p.read_text()
    s = s.replace("Active Card: V1-C07", "Active Card: V1-C08").replace("Active Card is V1-C07", "Active Card is V1-C08")
    s = s.replace("Next Roadmap Card: V1-C08", "Next Roadmap Card: V1-C09").replace("NO — C08 NOT_GRANTED", "NO — C09 NOT_GRANTED")
    s = s.replace("Next Roadmap Card: V1-C09 — Trade Flow & CVD", "Next Roadmap Card: V1-C09 — Derivatives & Volatility")
    s = s.replace("V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_NOT_VERIFIED", "V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED\nV1-C08 Authorization: START_GRANTED")
    s = re.sub(r"(^\| V1-C07 \|[^|]+\|) READY_FOR_HUMAN_REVIEW \| YES \| PASS \| READY_FOR_HUMAN_REVIEW", r"\1 COMPLETE | YES | PASS | COMPLETE", s, flags=re.M)
    s = re.sub(r"(^\| V1-C08 \|[^|]+\|) NOT_STARTED \| NO \| NOT_RUN \| PENDING", r"\1 READY_FOR_HUMAN_REVIEW | YES | PASS | READY_FOR_HUMAN_REVIEW", s, flags=re.M)
    start=s.index("Current active-Card record:"); end=s.index("Current active-Card Contract/Risk Map:",start)
    s=s[:start]+s[start:end].replace("Card ID: V1-C07", "Card ID: V1-C08").replace("Title: Order Book & Liquidity Analytics", "Title: Trade Flow & CVD")+s[end:]
    a=s.index("Current active-Card record:");b=s.index("Card Integration Record:",a)
    s=s[:a]+re.sub(r"^Human Delivery Approval:.*$", "Human Delivery Approval: NOT_GRANTED", s[a:b], flags=re.M)+s[b:]
    s=re.sub(r"^Git Branch:.*$", "Git Branch: " + branch, s, count=1, flags=re.M)
    s=re.sub(r"^Git Checkpoint:.*$", "Git Checkpoint: " + base, s, count=1, flags=re.M)
    p.write_text(s)
    for name,value in {
        "Card ID":"V1-C08", "Source Branch":branch, "Base SHA":base, "Source Commit":"DISCOVER", "Merge Anchor":"DISCOVER", "PR":"DISCOVER",
        "Protected Paths":"future.txt", "Integrated Paths":"PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, future.txt",
        "Human Merge Approval":"NOT_GRANTED", "Correction Branch":"NONE", "Correction Base SHA":"NONE",
        "Correction Paths":"NONE", "Correction Authorization":"NOT_GRANTED", "Correction Diff SHA-256":"NONE"}.items():
        field(repo,name,value)
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md"; s=p.read_text(); start=s.index("## V1-C07 "); end=s.index("## V1-C08 ",start); after=s.index("## V1-C09 ",end)
    original=s[start:end]; hypothetical=original.replace("V1-C07 — Order Book & Liquidity Analytics", "V1-C08 — Trade Flow & CVD")
    hypothetical=hypothetical.replace("- Branch: card/v1-c07-order-book-liquidity", "- Branch: "+branch).replace("- Base SHA: "+BASE, "- Base SHA: "+base)
    hypothetical=re.sub(r"^- Candidate Diff SHA-256:.*$", "- Candidate Diff SHA-256: PENDING", hypothetical, flags=re.M)
    closed=original.replace("**Status:** READY_FOR_HUMAN_REVIEW", "**Status:** COMPLETE",1)
    closed += "\n### Delivery Verification\nState: POST_MERGE_VERIFIED\nSource Branch: card/v1-c07-order-book-liquidity\nBase SHA: "+BASE+"\nAudit Digest: 433d000025974a91a19763b7c296abed77657543516fa5c901550ec33cc17e76\nSource Commit: "+SOURCE+"\nMerge Anchor: "+ANCHOR+"\nValidated Main: "+base+"\nHosted Run: 123\nLocal Validation Evidence: synthetic previous-Card closure only\nClosure Approval: GRANTED — synthetic only\n\n"
    s=s[:start]+closed+hypothetical+s[after:];p.write_text(s)
    (repo/"future.txt").write_text("hypothetical test payload, not a real Card implementation\n")
    if broken:
        p=repo/"PROJECT_CONTROL.md"; p.write_text(re.sub(r"^Card Integration Record:\n\n```text\n.*?^```\n\n", "", p.read_text(), flags=re.M|re.S))
    digest=c.worktree_candidate_identity(repo,base)["Candidate Diff SHA-256"]
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";p.write_text(p.read_text().replace("- Candidate Diff SHA-256: PENDING", "- Candidate Diff SHA-256: "+digest))
    git(repo,"add",".");git(repo,"commit","-qm","synthetic future source, not real approval")
    return base,git(repo,"rev-parse","HEAD"),branch


@pytest.mark.parametrize("broken",[False,True])
def test_prospective_squash_exercises_production_path(repo,broken):
    base,head,branch=future_candidate(repo,broken=broken)
    before=git(repo,"status","--porcelain")
    source_check=subprocess.run([sys.executable,"scripts/harness_consistency_check.py"],cwd=repo,env={**ENV,"PYTHONPATH":str(repo/"src")},text=True,capture_output=True)
    assert source_check.returncode==0,source_check.stdout+source_check.stderr
    r=subprocess.run([sys.executable,"scripts/check_maintenance_integration.py","--base",base,"--head",head,"--branch",branch],cwd=repo,env={**ENV,"PYTHONPATH":str(repo/"src")},text=True,capture_output=True)
    assert (r.returncode==0) is (not broken),r.stdout+r.stderr
    if broken:
        assert "GIT_BRANCH_STATE_MISMATCH" in r.stdout and "AUDITED_CANDIDATE_BRANCH_MISMATCH" in r.stdout
    else:
        assert "PROSPECTIVE_INTEGRATION" in r.stdout and "CARD_COMPLETE: NO" in r.stdout
    assert git(repo,"status","--porcelain")==before
    assert git(repo,"rev-parse","HEAD")==head


def test_missing_record_retains_original_failures(repo,monkeypatch):
    p=repo/"PROJECT_CONTROL.md";p.write_text(re.sub(r"^Card Integration Record:\n\n```text\n.*?^```\n\n","",p.read_text(),flags=re.M|re.S))
    assert check(repo,monkeypatch)==(False,())


def test_subsequent_change_same_allowed_path_still_requires_exact_digest(repo,monkeypatch):
    integrate_correction(repo)
    p=repo/"scripts/harness_consistency_check.py";p.write_text(p.read_text()+"\n# not in reviewed correction\n")
    git(repo,"add",".");git(repo,"commit","-qm","synthetic unreviewed drift")
    git(repo,"update-ref","refs/remotes/origin/main",git(repo,"rev-parse","HEAD"))
    assert check(repo,monkeypatch)==(False,("CARD_INTEGRATION_CORRECTION_DIGEST_MISMATCH",))


def test_github_merge_evidence_checks_exact_external_relationship(monkeypatch):
    import io
    import urllib.request
    value={"number":15,"state":"closed","merged":True,"merge_commit_sha":ANCHOR,"head":{"sha":SOURCE,"ref":"card/v1-c07-order-book-liquidity","repo":{"full_name":"jo-soroush/traid-market-intelligence"}},"base":{"sha":BASE,"ref":"main","repo":{"full_name":"jo-soroush/traid-market-intelligence"}}}
    monkeypatch.setattr(urllib.request,"urlopen",lambda *a,**k:io.BytesIO(json.dumps(value).encode()))
    assert c.github_card_merge_issues("15",SOURCE,BASE,ANCHOR,"card/v1-c07-order-book-liquidity")==()
    value["merged"]=False
    assert c.github_card_merge_issues("15",SOURCE,BASE,ANCHOR,"card/v1-c07-order-book-liquidity")==("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",)


@pytest.mark.parametrize("conclusion",["success","failure",None])
def test_closure_checks_actual_hosted_run_and_steps(repo,monkeypatch,conclusion):
    import io
    import urllib.request
    run={"status":"completed" if conclusion else "in_progress","conclusion":conclusion,"head_sha":ANCHOR,"head_branch":"main","event":"push","path":".github/workflows/ci.yml"}
    names=["Install from isolated committed source","Run pytest","Run bash scripts/check_secrets.sh","Run python scripts/harness_consistency_check.py"]
    jobs={"jobs":[{"name":"test","conclusion":"success","steps":[{"name":name,"conclusion":"success"} for name in names]}]}
    monkeypatch.setattr(urllib.request,"urlopen",lambda request,**k:io.BytesIO(json.dumps(jobs if "/jobs?" in request.full_url else run).encode()))
    result=c.github_card_closure_issues("PASS — run:123 sha:"+ANCHOR+" local:synthetic-approved-local-validation",repo,ANCHOR)
    assert result==(() if conclusion=="success" else ("CARD_CLOSURE_HOSTED_NOT_VERIFIED",))
    if conclusion=="success":
        jobs["jobs"][0]["steps"].pop()
        assert c.github_card_closure_issues("PASS — run:123 sha:"+ANCHOR+" local:synthetic",repo,ANCHOR)==("CARD_CLOSURE_REQUIRED_CHECK_MISSING",)


def test_unauthorized_next_card_rejected_before_integration(repo,monkeypatch):
    p=repo/"PROJECT_CONTROL.md";p.write_text(p.read_text().replace("Next Card Authorized: NO — C08 NOT_GRANTED","Next Card Authorized: YES — forged"));freeze(repo)
    assert check(repo,monkeypatch,BRANCH)==(False,("NEXT_CARD_AUTHORIZATION_PRESENT",))


def complete_fixture(repo, validation_sha):
    p=repo/"PROJECT_CONTROL.md";s=p.read_text()
    s=s.replace("Active Card: V1-C07", "Active Card: NONE").replace("Active Card State: READY_FOR_HUMAN_REVIEW", "Active Card State: NONE")
    s=s.replace("Active Card is V1-C07", "Active Card is NONE")
    s=s.replace("V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_NOT_VERIFIED", "V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED")
    s=re.sub(r"(^\| V1-C07 \|[^|]+\|) READY_FOR_HUMAN_REVIEW \| YES \| PASS \| READY_FOR_HUMAN_REVIEW",r"\1 COMPLETE | YES | PASS | COMPLETE",s,flags=re.M)
    a=s.index("Current active-Card record:");b=s.index("Card Integration Record:",a)
    block=s[a:b].replace("Current active-Card record:","Delivered-Card record:").replace("State: READY_FOR_HUMAN_REVIEW","State: COMPLETE").replace("Delivery Verified: NO","Delivery Verified: YES — synthetic fixture")
    p.write_text(s[:a]+block+s[b:])
    field(repo,"Closure Approval","GRANTED — synthetic explicit closure fixture")
    field(repo,"Post-Merge Verification","PASS — run:123 sha:"+validation_sha+" local:synthetic-local-validation")
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";s=p.read_text();start=s.index("## V1-C07 ");end=s.index("## V1-C08 ",start)
    closed=s[start:end].replace("**Status:** READY_FOR_HUMAN_REVIEW","**Status:** COMPLETE",1)
    closed += "\n### Delivery Verification\nState: POST_MERGE_VERIFIED\nSource Branch: card/v1-c07-order-book-liquidity\nBase SHA: "+BASE+"\nAudit Digest: 433d000025974a91a19763b7c296abed77657543516fa5c901550ec33cc17e76\nSource Commit: "+SOURCE+"\nMerge Anchor: "+ANCHOR+"\nValidated Main: "+validation_sha+"\nHosted Run: 123\nLocal Validation Evidence: synthetic-local-validation\nClosure Approval: GRANTED — synthetic explicit closure fixture\n\n"
    p.write_text(s[:start]+closed+s[end:])
    # Closure records a transition after verified source; it must not rewrite
    # the independently reviewed correction digest.


@pytest.mark.parametrize("verified",[False,True])
def test_complete_requires_coordinated_state_approval_and_real_verification(repo,monkeypatch,verified):
    integrate_correction(repo);validation_sha=git(repo,"rev-parse","HEAD")
    complete_fixture(repo,validation_sha);integrate_correction(repo)
    monkeypatch.setattr(c,"github_card_merge_issues",lambda *a:())
    # Only the external service response is mocked; state, lineage, scope,
    # immutable audit, current digest and all other production gates execute.
    monkeypatch.setattr(c,"github_card_closure_issues",lambda *a:() if verified else ("CARD_CLOSURE_HOSTED_NOT_VERIFIED",))
    result=c.card_integration_issues((repo/"PROJECT_CONTROL.md").read_text(),(repo/"TRAID_CARD_EVIDENCE_MAP.md").read_text(),repo,"main",verify_external=True)
    assert result==((True,()) if verified else (False,("CARD_CLOSURE_HOSTED_NOT_VERIFIED",)))
    command="import sys; sys.path.insert(0,'scripts'); import harness_consistency_check as m; m.github_card_merge_issues=lambda *a: (); m.github_card_closure_issues=lambda *a: "+("()" if verified else "('CARD_CLOSURE_HOSTED_NOT_VERIFIED',)")+"; raise SystemExit(m.main(verify_external=True))"
    r=subprocess.run([sys.executable,"-c",command],cwd=repo,env={**ENV,"PYTHONPATH":str(repo/"src")},text=True,capture_output=True)
    assert (r.returncode==0) is verified,r.stdout+r.stderr
    if verified:
        assert "VERIFIED_COMPLETE" in r.stdout and "CARD_COMPLETE: YES" in r.stdout


@pytest.mark.parametrize("kind",["missing","failed","identity"])
def test_main_correction_requires_its_own_review(repo,monkeypatch,kind):
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";s=p.read_text();a=s.index("## 26. Card Integration Lifecycle Correction");tail=s[a:]
    if kind=="missing":
        tail=tail.replace("### Independent Audit","### No review")
    elif kind=="failed":
        tail=tail.replace("- Status: PASS","- Status: BLOCKED")
    else:
        tail=re.sub(r"^- Candidate Diff SHA-256:.*$","- Candidate Diff SHA-256: "+"0"*64,tail,flags=re.M)
    p.write_text(s[:a]+tail)
    if kind=="missing":
        # Structural changes remain hashed and require their own fixture freeze.
        field(repo,"Correction Diff SHA-256",c.worktree_candidate_identity(repo,ANCHOR,recorded_branch=BRANCH)["Candidate Diff SHA-256"])
    integrate_correction(repo)
    reason={"missing":"CARD_INTEGRATION_CORRECTION_AUDIT_MISSING","failed":"CARD_INTEGRATION_CORRECTION_AUDIT_UNRESOLVED","identity":"CARD_INTEGRATION_CORRECTION_AUDIT_IDENTITY_MISMATCH"}[kind]
    assert check(repo,monkeypatch)==(False,(reason,))


def test_later_explicit_merge_receipt_supersedes_frozen_source_approval(repo,monkeypatch):
    p=repo/"PROJECT_CONTROL.md";s=p.read_text();a=s.index("Current active-Card record:");b=s.index("Card Integration Record:",a)
    block=re.sub(r"^Human Delivery Approval:.*$","Human Delivery Approval: NOT_GRANTED",s[a:b],flags=re.M)
    p.write_text(s[:a]+block+s[b:]);freeze(repo)
    assert check(repo,monkeypatch,BRANCH)==(True,())
    field(repo,"Human Merge Approval","NOT_GRANTED");freeze(repo)
    assert check(repo,monkeypatch,BRANCH,verify_external=True)==(False,("CARD_INTEGRATION_APPROVAL_MISSING",))


def test_original_active_source_passes_and_changed_source_fails(repo):
    integrate_correction(repo)
    branch="card/v1-c07-order-book-liquidity"
    git(repo,"checkout","-B",branch,SOURCE)
    record=c.CardRecord("V1-C07","Order Book & Liquidity Analytics","READY_FOR_HUMAN_REVIEW",True)
    evidence=(repo/"TRAID_CARD_EVIDENCE_MAP.md").read_text()
    assert c.active_card_candidate_issues(evidence,record,repo,branch)==()
    p=repo/"src/traid/liquidity/analytics.py";p.write_text(p.read_text()+"\n# stale reviewed candidate\n")
    assert "AUDITED_CANDIDATE_CHANGED:Candidate Diff SHA-256" in ",".join(c.active_card_candidate_issues(evidence,record,repo,branch))


def test_normalization_excludes_only_designated_self_digest():
    raw=b"FILE\0## 6. Active Card Record\n\nCard Integration Record:\n\n```text\nCorrection Diff SHA-256: old\nCorrection Authorization: NOT_GRANTED\n```\n\n## 7. Authorization Ledger\nCorrection Diff SHA-256: material\n"
    normalized=c._normalize_integration_results("PROJECT_CONTROL.md",raw)
    assert b"Correction Diff SHA-256: <integration-result>" in normalized
    assert b"Correction Diff SHA-256: material" in normalized
    assert c._normalize_integration_results("other.md",raw)==raw
    assert c._normalize_integration_results("PROJECT_CONTROL.md",raw.replace(b"NOT_GRANTED",b"GRANTED"))!=normalized


def test_isolated_digest_gate_mutant_is_detected(repo,monkeypatch,tmp_path):
    import importlib.util
    integrate_correction(repo)
    p=repo/"GIT_WORKFLOW.md";p.write_text(p.read_text()+"\nUnreviewed same-path alteration.\n")
    git(repo,"add",".");git(repo,"commit","-qm","synthetic drift, not approved")
    git(repo,"update-ref","refs/remotes/origin/main",git(repo,"rev-parse","HEAD"))
    assert check(repo,monkeypatch)==(False,("CARD_INTEGRATION_CORRECTION_DIGEST_MISMATCH",))
    source=(ROOT/"scripts/harness_consistency_check.py").read_text()
    needle="if not SHA256.fullmatch(expected) or expected != actual:"
    assert source.count(needle)==1
    mutant=tmp_path/"mutant.py";mutant.write_text(source.replace(needle,"if not SHA256.fullmatch(expected):"))
    spec=importlib.util.spec_from_file_location("isolated_card_mutant",mutant)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    monkeypatch.setattr(module,"github_card_merge_issues",lambda *a:())
    # Removing only this security gate accepts the exact negative case rejected
    # by the production oracle above. The original checker is never modified.
    assert module.card_integration_issues((repo/"PROJECT_CONTROL.md").read_text(),(repo/"TRAID_CARD_EVIDENCE_MAP.md").read_text(),repo,"main")== (True,())


def test_external_evidence_unavailable_fails_closed(monkeypatch,repo):
    import urllib.request
    def unavailable(*a,**k):
        raise OSError("synthetic outage")
    monkeypatch.setattr(urllib.request,"urlopen",unavailable)
    assert c.github_card_merge_issues("15",SOURCE,BASE,ANCHOR,"card/v1-c07-order-book-liquidity")==("CARD_INTEGRATION_GITHUB_EVIDENCE_UNAVAILABLE",)
    assert c.github_card_closure_issues("PASS — run:123 sha:"+ANCHOR+" local:synthetic",repo,ANCHOR)==("CARD_CLOSURE_HOSTED_EVIDENCE_UNAVAILABLE",)


def test_forged_completion_ledger_without_delivery_receipt_is_rejected(repo):
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";s=p.read_text();a=s.index("## V1-C07 ");b=s.index("## V1-C08 ",a)
    s=s[:a]+s[a:b].replace("**Status:** READY_FOR_HUMAN_REVIEW","**Status:** COMPLETE",1)+s[b:]
    result=c.card_documentation_issues(s,c.CardRecord("V1-C07","Order Book & Liquidity Analytics","COMPLETE",True))
    assert "V1-C07:DELIVERY_VERIFICATION_RECEIPT_MISSING_OR_INVALID" in result


@pytest.mark.parametrize("kind",["failed","missing_identity"])
def test_prospective_rejects_unaccepted_original_audit(repo,kind):
    base,head,branch=future_candidate(repo)
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";s=p.read_text();a=s.index("## V1-C08 ");b=s.index("## V1-C09 ",a);block=s[a:b]
    if kind=="failed":
        block=block.replace("- Status: PASS","- Status: BLOCKED")
    else:
        block=re.sub(r"^- Candidate Diff SHA-256:.*\n","",block,flags=re.M)
    p.write_text(s[:a]+block+s[b:]);git(repo,"add",".");git(repo,"commit","-qm","synthetic rejected audit fixture")
    head=git(repo,"rev-parse","HEAD")
    r=subprocess.run([sys.executable,"scripts/check_maintenance_integration.py","--base",base,"--head",head,"--branch",branch],cwd=repo,env={**ENV,"PYTHONPATH":str(repo/"src")},text=True,capture_output=True)
    assert r.returncode!=0
    assert ("INDEPENDENT_AUDIT_NOT_COMPLETE" if kind=="failed" else "INDEPENDENT_AUDIT_DIFF_SHA256_INVALID") in r.stdout,r.stdout+r.stderr


def test_future_pr_discovery_fetches_authoritative_detail(monkeypatch):
    import io
    import urllib.request
    listing=[{"number":15,"head":{"sha":SOURCE},"merge_commit_sha":ANCHOR}]
    detail={"number":15,"state":"closed","merged":True,"merge_commit_sha":ANCHOR,"head":{"sha":SOURCE,"ref":"card/v1-c07-order-book-liquidity","repo":{"full_name":"jo-soroush/traid-market-intelligence"}},"base":{"sha":BASE,"ref":"main","repo":{"full_name":"jo-soroush/traid-market-intelligence"}}}
    urls=[]
    def response(request,**kwargs):
        urls.append(request.full_url)
        return io.BytesIO(json.dumps(listing if "?" in request.full_url else detail).encode())
    monkeypatch.setattr(urllib.request,"urlopen",response)
    assert c.github_card_merge_issues("DISCOVER",SOURCE,BASE,ANCHOR,"card/v1-c07-order-book-liquidity")==()
    assert len(urls)==2 and urls[1].endswith("/pulls/15")


def test_merge_receipt_normalization_never_grants_authority(repo,monkeypatch):
    before=c.worktree_candidate_identity(repo,ANCHOR,recorded_branch=BRANCH)["Candidate Diff SHA-256"]
    field(repo,"Human Merge Approval","NOT_GRANTED")
    assert c.worktree_candidate_identity(repo,ANCHOR,recorded_branch=BRANCH)["Candidate Diff SHA-256"]==before
    assert check(repo,monkeypatch,BRANCH,verify_external=True)==(False,("CARD_INTEGRATION_APPROVAL_MISSING",))
    field(repo,"Human Merge Approval","GRANTED — synthetic later explicit receipt")
    assert c.worktree_candidate_identity(repo,ANCHOR,recorded_branch=BRANCH)["Candidate Diff SHA-256"]==before
    assert check(repo,monkeypatch,BRANCH)==(True,())
    field(repo,"Correction Authorization","NOT_GRANTED")
    assert c.worktree_candidate_identity(repo,ANCHOR,recorded_branch=BRANCH)["Candidate Diff SHA-256"]!=before


def test_late_merge_receipt_preserves_source_review_and_simulates(repo):
    base,head,branch=future_candidate(repo)
    digest=c.worktree_candidate_identity(repo,base)["Candidate Diff SHA-256"]
    evidence=(repo/"TRAID_CARD_EVIDENCE_MAP.md").read_bytes()
    field(repo,"Human Merge Approval","NOT_GRANTED")
    assert c.worktree_candidate_identity(repo,base)["Candidate Diff SHA-256"]==digest
    field(repo,"Human Merge Approval","GRANTED — synthetic post-audit merge approval checkpoint")
    assert c.worktree_candidate_identity(repo,base)["Candidate Diff SHA-256"]==digest
    git(repo,"add",".");git(repo,"commit","-qm","synthetic same-PR result-only approval checkpoint")
    assert (repo/"TRAID_CARD_EVIDENCE_MAP.md").read_bytes()==evidence
    head=git(repo,"rev-parse","HEAD")
    r=subprocess.run([sys.executable,"scripts/check_maintenance_integration.py","--base",base,"--head",head,"--branch",branch],cwd=repo,env={**ENV,"PYTHONPATH":str(repo/"src")},text=True,capture_output=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert "CARD_COMPLETE: NO" in r.stdout


def test_correction_implementation_permission_is_not_merge_permission(repo,monkeypatch):
    p=repo/"TRAID_CARD_EVIDENCE_MAP.md";s=p.read_text();a=s.index("## 26. Card Integration Lifecycle Correction")
    tail=re.sub(r"^- Delivery authorization/performance:.*$","- Delivery authorization/performance: NOT_GRANTED / NOT_PERFORMED — local only",s[a:],flags=re.M)
    p.write_text(s[:a]+tail);integrate_correction(repo)
    assert check(repo,monkeypatch,verify_external=True)==(False,("CARD_INTEGRATION_CORRECTION_DELIVERY_NOT_GRANTED",))


def simulate(repo, base, head, branch):
    return subprocess.run(
        [sys.executable, "scripts/check_maintenance_integration.py", "--base", base,
         "--head", head, "--branch", branch], cwd=repo,
        env={**ENV, "PYTHONPATH": str(repo / "src")}, text=True, capture_output=True,
    )


@pytest.mark.parametrize("mutation,reason", [
    (None, None),
    ("failed_review", "CARD_INTEGRATION_CORRECTION_AUDIT_UNRESOLVED"),
    ("wrong_branch", "CARD_INTEGRATION_PROSPECTIVE_BRANCH_MISMATCH"),
    ("protected", "CARD_INTEGRATION_PROTECTED_CONTENT_CHANGED"),
    ("missing_authorization", "CARD_INTEGRATION_UNAUTHORIZED_SUBSEQUENT_CHANGE"),
])
def test_correction_pr_uses_actual_production_squash_without_merge_approval(repo, mutation, reason):
    git(repo, "checkout", "-B", BRANCH)
    field(repo, "Human Merge Approval", "NOT_GRANTED")
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    text = p.read_text(); start = text.index("## 26. Card Integration Lifecycle Correction")
    tail = re.sub(r"^- Delivery authorization/performance:.*$",
                  "- Delivery authorization/performance: NOT_GRANTED / NOT_PERFORMED — synthetic pre-merge review",
                  text[start:], flags=re.M)
    if mutation == "failed_review":
        tail = tail.replace("- Status: PASS", "- Status: BLOCKED")
    p.write_text(text[:start] + tail)
    if mutation == "protected":
        p = repo / "src/traid/liquidity/analytics.py"; p.write_text(p.read_text() + "\n# forbidden\n")
    if mutation == "missing_authorization":
        field(repo, "Correction Authorization", "NOT_GRANTED")
    freeze(repo)
    git(repo, "add", "."); git(repo, "commit", "-qm", "synthetic correction source only")
    branch = BRANCH
    if mutation == "wrong_branch":
        branch = "fix/card-integration-unapproved"; git(repo, "checkout", "-b", branch)
    head = git(repo, "rev-parse", "HEAD")
    before = git(repo, "status", "--porcelain")
    if mutation is None:
        source_check = subprocess.run([sys.executable, "scripts/harness_consistency_check.py"], cwd=repo,
                                      env={**ENV, "PYTHONPATH": str(repo / "src")}, text=True, capture_output=True)
        assert source_check.returncode == 0, source_check.stdout + source_check.stderr
        assert "CORRECTION_DELIVERY: NOT_GRANTED" in source_check.stdout
    result = simulate(repo, ANCHOR, head, branch)
    assert (result.returncode == 0) is (reason is None), result.stdout + result.stderr
    if reason:
        assert reason in result.stdout, result.stdout + result.stderr
    else:
        assert "PROSPECTIVE_INTEGRATION" in result.stdout
        assert "EXTERNAL_ATTESTATION: NOT_RUN; DELIVERY_NOT_VERIFIED" in result.stdout
        assert "CARD_COMPLETE: NO" in result.stdout
    assert git(repo, "status", "--porcelain") == before
    assert git(repo, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("branch", ["feature/unrecognized", "fix/unrelated", "main", ""])
def test_unsupported_integration_never_succeeds(repo, branch):
    result = simulate(repo, ANCHOR, ANCHOR, branch)
    assert result.returncode != 0
    assert "BLOCKED — unsupported source branch" in result.stdout


def test_local_pending_is_deterministic_offline_and_not_delivery(repo, monkeypatch):
    integrate_correction(repo)
    def forbidden(*args, **kwargs):
        raise AssertionError("local technical validation must not invoke GitHub")
    monkeypatch.setattr(c, "github_card_merge_issues", forbidden)
    monkeypatch.setattr(c, "github_card_closure_issues", forbidden)
    assert c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                    (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, "main") == (True, ())
    result = subprocess.run([sys.executable, "scripts/harness_consistency_check.py"], cwd=repo,
                            env={**ENV, "PYTHONPATH": str(repo / "src")}, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXTERNAL_ATTESTATION: NOT_RUN; DELIVERY_NOT_VERIFIED" in result.stdout
    assert "CARD_COMPLETE: NO" in result.stdout


def test_documentary_complete_requires_explicit_external_attestation(repo, monkeypatch):
    integrate_correction(repo)
    complete_fixture(repo, git(repo, "rev-parse", "HEAD")); integrate_correction(repo)
    assert check(repo, monkeypatch) == (False, ("CARD_CLOSURE_EXTERNAL_VERIFICATION_REQUIRED",))


@pytest.mark.parametrize("issue", ["CARD_INTEGRATION_GITHUB_EVIDENCE_UNAVAILABLE",
                                    "CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH"])
def test_explicit_attestation_fails_closed_on_external_unknown_or_contradiction(repo, monkeypatch, issue):
    integrate_correction(repo)
    monkeypatch.setattr(c, "github_card_merge_issues", lambda *args: (issue,))
    assert c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                    (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, "main",
                                    verify_external=True) == (False, (issue,))


def test_external_attestation_checks_correction_merge_not_just_original_card(repo, monkeypatch):
    integrate_correction(repo)
    observed = []
    def external(pr, source, base, anchor, branch):
        observed.append((pr, source, base, anchor, branch))
        return () if branch != BRANCH else ("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",)
    monkeypatch.setattr(c, "github_card_merge_issues", external)
    assert c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                    (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, "main",
                                    verify_external=True) == (False, ("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",))
    assert [entry[-1] for entry in observed] == ["card/v1-c07-order-book-liquidity", BRANCH]


def test_forged_correction_source_reference_rejected(repo, monkeypatch):
    integrate_correction(repo)
    git(repo, "update-ref", "refs/remotes/origin/" + BRANCH, SOURCE)
    assert check(repo, monkeypatch, verify_external=True) == (False, ("CARD_INTEGRATION_CORRECTION_SOURCE_ANCESTRY_INVALID",))


def test_invalid_approval_token_rejected_even_by_local_checker(repo, monkeypatch):
    field(repo, "Human Merge Approval", "PASS — forged permission")
    freeze(repo)
    assert check(repo, monkeypatch, BRANCH) == (False, ("CARD_INTEGRATION_APPROVAL_INVALID",))


@pytest.mark.parametrize("external", ["false", "true"])
def test_ci_selects_external_stage_and_propagates_failure(tmp_path, external):
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "github.event_name == 'push' && github.ref_name == 'main'" in workflow
    section = workflow.split("- name: Run python scripts/harness_consistency_check.py\n", 1)[1]
    block = section.split("        run: |\n", 1)[1].split("      - ", 1)[0]
    shell = "\n".join(line[10:] for line in block.splitlines())
    wrapper = tmp_path / "python"
    wrapper.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\"\nexit 7\n")
    wrapper.chmod(0o755)
    result = subprocess.run(["bash", "-e", "-c", shell], text=True, capture_output=True,
                            env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
                                 "VERIFY_EXTERNAL": external})
    assert result.returncode == 7
    assert ("--verify-external" in result.stdout) is (external == "true")


def test_missing_start_authorization_remains_fatal(repo, monkeypatch):
    p = repo / "PROJECT_CONTROL.md"
    text = p.read_text(); a = text.index("Current active-Card record:"); b = text.index("Card Integration Record:", a)
    text = text[:a] + re.sub(r"^Human Start Approval:.*$", "Human Start Approval: NOT_GRANTED", text[a:b], flags=re.M) + text[b:]
    p.write_text(text); freeze(repo)
    assert check(repo, monkeypatch, BRANCH) == (False, ("ACTIVE_CARD_START_APPROVAL_MISSING",))


def test_future_normal_card_closure_needs_no_fake_correction_record(repo, monkeypatch):
    base, source, branch = future_candidate(repo)
    git(repo, "checkout", "-B", "main", base)
    git(repo, "merge", "--squash", source); git(repo, "commit", "-qm", "synthetic future squash")
    anchor = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/" + branch, source)
    p = repo / "PROJECT_CONTROL.md"; text = p.read_text()
    text = text.replace("Active Card: V1-C08", "Active Card: NONE").replace("Active Card is V1-C08", "Active Card is NONE")
    text = text.replace("Active Card State: READY_FOR_HUMAN_REVIEW", "Active Card State: NONE")
    text = text.replace("V1-C08 Authorization: START_GRANTED", "V1-C08 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED")
    text = re.sub(r"(^\| V1-C08 \|[^|]+\|) READY_FOR_HUMAN_REVIEW \| YES \| PASS \| READY_FOR_HUMAN_REVIEW",
                  r"\1 COMPLETE | YES | PASS | COMPLETE", text, flags=re.M)
    a = text.index("Current active-Card record:"); b = text.index("Card Integration Record:", a)
    block = text[a:b].replace("Current active-Card record:", "Delivered-Card record:").replace("State: READY_FOR_HUMAN_REVIEW", "State: COMPLETE")
    p.write_text(text[:a] + block + text[b:])
    field(repo, "Human Merge Approval", "GRANTED — synthetic explicit future merge instruction")
    field(repo, "Closure Approval", "GRANTED — synthetic explicit future closure instruction")
    field(repo, "Post-Merge Verification", "PASS — run:123 sha:" + anchor + " local:synthetic-future-local-proof")
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"; text = p.read_text()
    a = text.index("## V1-C08 "); b = text.index("## V1-C09 ", a)
    section = text[a:b].replace("**Status:** READY_FOR_HUMAN_REVIEW", "**Status:** COMPLETE", 1)
    digest = re.search(r"^- Candidate Diff SHA-256: (.+)$", section, re.M).group(1)
    section += ("\n### Delivery Verification\nState: POST_MERGE_VERIFIED\nSource Branch: " + branch
                + "\nBase SHA: " + base + "\nAudit Digest: " + digest + "\nSource Commit: " + source
                + "\nMerge Anchor: " + anchor + "\nValidated Main: " + anchor + "\nHosted Run: 123"
                + "\nLocal Validation Evidence: synthetic-future-local-proof"
                + "\nClosure Approval: GRANTED — synthetic explicit future closure instruction\n\n")
    p.write_text(text[:a] + section + text[b:])
    git(repo, "add", "."); git(repo, "commit", "-qm", "synthetic normal closure record")
    git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
    monkeypatch.setattr(c, "github_card_merge_issues", lambda *args: ())
    monkeypatch.setattr(c, "github_card_closure_issues", lambda *args: ())
    assert c.card_integration_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                    (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo, "main",
                                    verify_external=True) == (True, ())
    assert "Correction Branch: NONE" in (repo / "PROJECT_CONTROL.md").read_text()


@pytest.mark.parametrize("issue", [None, "CARD_CLOSURE_HOSTED_NOT_VERIFIED"])
def test_archived_completion_cannot_hide_missing_hosted_proof(repo, monkeypatch, issue):
    base, source, branch = future_candidate(repo)
    monkeypatch.setattr(c, "github_card_merge_issues", lambda *args: ())
    monkeypatch.setattr(c, "github_card_closure_issues", lambda *args: () if issue is None else (issue,))
    result = c.historical_card_delivery_issues((repo / "PROJECT_CONTROL.md").read_text(),
                                              (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text(), repo)
    assert result == (() if issue is None else ("V1-C07:" + issue,))
