import unittest
from unittest.mock import MagicMock, patch
import datetime

# Mock DATABASE_URL environment variable
import os
os.environ["DATABASE_URL"] = "postgresql://mock_user:mock_pass@localhost:5432/mock_db"

import database

class MockDatetime15(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 7, 15, 12, 0, 0, tzinfo=tz)

class MockDatetime14(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 7, 14, 12, 0, 0, tzinfo=tz)

class TestDatabase(unittest.TestCase):
    @patch('database.get_connection')
    @patch('datetime.datetime', MockDatetime15)
    def test_free_user_quota_reset_on_new_month(self, mock_get_conn):
        # Setup mock database cursor to return free user data
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # Last reset was 2026-06-15
        mock_cur.fetchone.return_value = {
            'current_mode': 'HUMAN',
            'usage_month': '2026-06-15',
            'usage_count': 3,
            'purchased_quota': 0,
            'subscription_tier': 'FREE',
            'subscription_expiry': None
        }
        
        status = database.get_user_status_data("U12345", "2026-07")
        
        # Verify that usage_count is reset to 0
        self.assertEqual(status['usage'], 0)
        
        # Verify database update was called to reset usage_count and update reset date to 2026-07-15
        mock_cur.execute.assert_any_call(
            "UPDATE users SET usage_month = %s, usage_count = 0 WHERE user_id = %s",
            ("2026-07-15", "U12345")
        )

    @patch('database.get_connection')
    @patch('datetime.datetime', MockDatetime15)
    def test_subscribed_user_quota_resets_on_anniversary(self, mock_get_conn):
        # Setup mock database cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        future_expiry = "2027-07-15 12:00:00"
        
        # Last reset was 2026-06-15
        mock_cur.fetchone.return_value = {
            'current_mode': 'HUMAN',
            'usage_month': '2026-06-15',
            'usage_count': 12,
            'purchased_quota': 0,
            'subscription_tier': 'ADVANCED',
            'subscription_expiry': future_expiry
        }
        
        status = database.get_user_status_data("U12345", "2026-07")
        
        # Verify that usage_count is reset to 0 since anniversary date (15th) is reached
        self.assertEqual(status['usage'], 0)
        mock_cur.execute.assert_any_call(
            "UPDATE users SET usage_month = %s, usage_count = 0 WHERE user_id = %s",
            ("2026-07-15", "U12345")
        )

    @patch('database.get_connection')
    @patch('datetime.datetime', MockDatetime14)
    def test_subscribed_user_quota_no_reset_before_anniversary(self, mock_get_conn):
        # Setup mock database cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        future_expiry = "2027-07-15 12:00:00"
        
        # Last reset was 2026-06-15, anniversary day is 15th
        mock_cur.fetchone.return_value = {
            'current_mode': 'HUMAN',
            'usage_month': '2026-06-15',
            'usage_count': 12,
            'purchased_quota': 0,
            'subscription_tier': 'ADVANCED',
            'subscription_expiry': future_expiry
        }
        
        status = database.get_user_status_data("U12345", "2026-07")
        
        # Verify that usage_count is NOT reset because today (14th) is before the anniversary day (15th)
        self.assertEqual(status['usage'], 12)
        
        # Verify update was not triggered for reset
        for call in mock_cur.execute.call_args_list:
            args = call[0]
            if "UPDATE users" in args[0] and "usage_count = 0" in args[0]:
                self.fail("Should not reset usage count before anniversary date")

if __name__ == '__main__':
    unittest.main()
