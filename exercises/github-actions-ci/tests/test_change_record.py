from __future__ import annotations
import unittest
from change_record import MAX_TITLE_LENGTH, RecordValidationError, validate_record

class ChangeRecordValidationTests(unittest.TestCase):

    def valid_record(self) -> dict[str, object]:
        return {'title': 'Validate pull request metadata', 'summary': 'Reject incomplete change records before review.', 'checks': ['python -m unittest', 'workflow passed']}

    def test_accepts_a_complete_record(self) -> None:
        record = validate_record(self.valid_record())
        self.assertEqual(record['title'], 'Validate pull request metadata')
        self.assertEqual(len(record['checks']), 2)

    def test_rejects_a_non_object(self) -> None:
        with self.assertRaisesRegex(RecordValidationError, 'JSON object'):
            validate_record([])

    def test_rejects_missing_fields(self) -> None:
        with self.assertRaisesRegex(RecordValidationError, 'missing required field\\(s\\): checks, summary'):
            validate_record({'title': 'Only a title'})

    def test_rejects_unknown_fields(self) -> None:
        value = self.valid_record()
        value['reviewer'] = 'alice'
        with self.assertRaisesRegex(RecordValidationError, 'unknown field'):
            validate_record(value)

    def test_rejects_an_empty_title(self) -> None:
        value = self.valid_record()
        value['title'] = '   '
        with self.assertRaisesRegex(RecordValidationError, 'non-empty string'):
            validate_record(value)

    def test_rejects_a_title_over_the_limit(self) -> None:
        value = self.valid_record()
        value['title'] = 'x' * (MAX_TITLE_LENGTH + 1)
        with self.assertRaisesRegex(RecordValidationError, 'at most'):
            validate_record(value)

    def test_rejects_empty_checks(self) -> None:
        value = self.valid_record()
        value['checks'] = []
        with self.assertRaisesRegex(RecordValidationError, 'non-empty array'):
            validate_record(value)
