"""Offline checks for the CSV verifier and API failure handling; no remote calls."""
import csv
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sandbox_check as app


class Record(SimpleNamespace):
    def model_dump(self, **kwargs):
        return self.__dict__


def page(values):
    return SimpleNamespace(data=values, has_more=False)


class FakeClient:
    def __init__(self, status="idle", turn_status="completed", missing=False, invalid=False, stale=False):
        self.session = Record(id="sess", status=status, error="setup failed" if status == "failed" else None)
        self.turn = Record(id="turn", status=turn_status, subagent_id=None, error=None)
        self.deleted = False
        self.cancelled = False
        self.requests = []
        self.invalid = invalid
        artifacts = [Record(id="summary", path="/workspace/outputs/summary.json", turn_id="turn"),
                     Record(id="code", path="/workspace/outputs/calculate.py", turn_id="turn")]
        if missing:
            artifacts = artifacts[:1]
        if stale:
            artifacts[0].turn_id = "old-turn"
        self.turns = SimpleNamespace(list=lambda *a, **kw: page([self.turn]))
        self.items = SimpleNamespace(list=lambda *a, **kw: page([]))
        self.artifacts = SimpleNamespace(list=lambda *a, **kw: page(artifacts), content=self.content)
        self.events = SimpleNamespace(create=self.cancel)
        self.beta = SimpleNamespace(agents=SimpleNamespace(sessions=self))

    def with_options(self, **kwargs):
        self.requests.append(kwargs)
        return self

    def create(self, **kwargs):
        return self.session

    def retrieve(self, *args):
        return self.session

    def delete(self, *args):
        self.deleted = True

    def cancel(self, *args, **kwargs):
        self.cancelled = True

    def content(self, artifact_id, **kwargs):
        expected = app.make_dataset(42)[1]
        data = (b'{}' if self.invalid else json.dumps(expected).encode()) if artifact_id == "summary" else b"# saved code\n"
        return io.BytesIO(data)


class SandboxCheckTests(unittest.TestCase):
    def trial(self, client, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "trial"
            result = app.run_trial(client, 1, 42, directory, poll_seconds=0, **kwargs)
            self.assertEqual(json.loads((directory / "result.json").read_text()), result)
            return result

    def test_fixture_reproducible_and_independent_decimal_total(self):
        for seed in range(50):
            text, expected = app.make_dataset(seed)
            self.assertEqual((text, expected), app.make_dataset(seed))
            values = []
            for row in csv.DictReader(io.StringIO(text)):
                try:
                    values.append(Decimal(row['amount'].strip().replace('$', '').replace(',', '')))
                except Exception:
                    self.assertEqual(row['amount'], 'N/A')
            self.assertEqual(int(sum(values) * 100), expected['total_cents'])
            self.assertEqual(len(values), expected['valid_rows'])
            self.assertIn(',', next(row['amount'] for row in csv.DictReader(io.StringIO(text)) if ',' in row['amount']))

    def test_exact_comparison_and_schema(self):
        expected = app.make_dataset(42)[1]
        self.assertTrue(app.validate_summary(json.dumps(expected), expected)[1])
        wrong = dict(expected, total_cents=expected['total_cents'] + 1)
        self.assertFalse(app.validate_summary(json.dumps(wrong), expected)[1])
        for bad in [dict(expected, total_cents=True), dict(expected, valid_rows=5.0),
                    dict(expected, extra=1), {}, [], dict(expected, total_cents=float('nan'))]:
            with self.assertRaises(ValueError):
                app.validate_summary(json.dumps(bad), expected)
        with self.assertRaises(ValueError):
            app.validate_summary('{"total_cents":1,"total_cents":2,"valid_rows":5,"invalid_rows":1}', expected)

    def test_success_downloads_and_cleans_up(self):
        client = FakeClient()
        result = self.trial(client)
        self.assertEqual(result['outcome'], 'passed')
        self.assertTrue(client.deleted)
        self.assertEqual(set(result['artifact_ids']), {'summary.json', 'calculate.py'})
        self.assertTrue(all(r['max_retries'] == 0 for r in client.requests))
        self.assertLessEqual(result['timings']['download_complete_s'], result['timings']['verification_complete_s'])

    def test_distinct_failures_and_cleanup(self):
        for kwargs, outcome in [({'status':'failed'}, 'session_failed'),
                                ({'status':'requires_action'}, 'requires_action'),
                                ({'turn_status':'failed'}, 'turn_failed'),
                                ({'turn_status':'cancelled'}, 'turn_cancelled'),
                                ({'missing':True}, 'missing_artifact'),
                                ({'stale':True}, 'missing_artifact'),
                                ({'invalid':True}, 'invalid_summary')]:
            with self.subTest(outcome=outcome, kwargs=kwargs):
                client = FakeClient(**kwargs)
                result = self.trial(client)
                self.assertEqual(result['outcome'], outcome)
                self.assertFalse(result['correct'])
                self.assertTrue(client.deleted)

    def test_request_failure_still_cleans_up(self):
        client = FakeClient()
        client.retrieve = lambda *a: (_ for _ in ()).throw(RuntimeError('connection lost'))
        result = self.trial(client)
        self.assertEqual(result['outcome'], 'request_or_client_error')
        self.assertTrue(client.cancelled)
        self.assertTrue(client.deleted)

    def test_no_turn_deadline_cancels_and_deletes(self):
        client = FakeClient()
        client.turns.list = lambda *a, **kw: page([])
        ticks = iter(i / 100 for i in range(10000))
        with patch.object(app.time, 'monotonic', side_effect=lambda: next(ticks)):
            result = self.trial(client, timeout=0.1)
        self.assertEqual(result['outcome'], 'deadline_exceeded')
        self.assertTrue(client.cancelled)
        self.assertTrue(client.deleted)

    def test_cleanup_failure_preserves_correctness(self):
        client = FakeClient()
        client.delete = lambda *a: (_ for _ in ()).throw(RuntimeError('cannot delete'))
        result = self.trial(client)
        self.assertTrue(result['correct'])
        self.assertFalse(result['cleanup']['deleted'])
        self.assertIn('cannot delete', result['cleanup']['errors'][0])

    def test_zero_trials_rejected_without_sdk(self):
        with self.assertRaises(SystemExit) as exc:
            app.run(['0'])
        self.assertEqual(exc.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
