import unittest
import sqlite3
import time
import os
import sys
from unittest.mock import patch, MagicMock

# Adjust path to import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # This should be 'aegis_orchestrator_mvp'
src_path = os.path.join(project_root, "src")
data_path = os.path.join(project_root, "data") # For test database

if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create data directory if it doesn't exist
os.makedirs(data_path, exist_ok=True)

# Override _DB_FILE for testing before importing feedback
TEST_DB_FILE = os.path.join(data_path, "test_feedback.db")

# IMPORTANT: Mock the database path *before* feedback module is imported the first time
# by other test files or the module itself if it's reloaded.
# We also need to control the `con` object within feedback.
# One way is to allow `feedback.con` to be reassigned for tests.

# To ensure a clean state for feedback's global `con` and `_DB_FILE`
# we can try to reload the module or carefully manage its state.
if 'src.feedback' in sys.modules:
    del sys.modules['src.feedback']

# Now set the path for feedback to use during its import
_mock_db_path = MagicMock(return_value=TEST_DB_FILE)
with patch('src.feedback._DB_FILE', TEST_DB_FILE):
    from src import feedback # Import after patching

class TestFeedback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure the test database is clean before all tests in this class
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)
        
        # Re-initialize the connection in the feedback module to use the test DB
        # This requires feedback.py to be structured to allow `con` to be re-initialized
        # or by re-running its schema setup against the new TEST_DB_FILE.
        feedback.con = sqlite3.connect(TEST_DB_FILE)
        feedback.con.executescript(feedback._schema) # Use executescript for multi-statement schema
        feedback.con.commit()

    @classmethod
    def tearDownClass(cls):
        # Close the connection and remove the test database after all tests
        if feedback.con:
            feedback.con.close()
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)

    def setUp(self):
        # Clean the ab_stats table before each test method
        with feedback.con:
            feedback.con.execute("DELETE FROM ab_stats")
            feedback.con.commit()

    @patch('src.feedback.VARIANT_METRIC') # Mock Prometheus counter
    def test_record_new_success(self, mock_variant_metric_counter):
        feedback.record("pipe1", "varA", True, tool_name="TestTool")
        
        mock_variant_metric_counter.labels.assert_called_with("pipe1", "varA")
        mock_variant_metric_counter.labels.return_value.inc.assert_called_once()

        cur = feedback.con.execute("SELECT success, failure FROM ab_stats WHERE pipeline = 'pipe1' AND variant = 'varA'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1) # success
        self.assertEqual(row[1], 0) # failure

    @patch('src.feedback.VARIANT_METRIC')
    def test_record_new_failure(self, mock_variant_metric_counter):
        feedback.record("pipe1", "varB", False, tool_name="TestTool")
        cur = feedback.con.execute("SELECT success, failure FROM ab_stats WHERE pipeline = 'pipe1' AND variant = 'varB'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 0)
        self.assertEqual(row[1], 1)

    @patch('src.feedback.VARIANT_METRIC')
    def test_record_multiple_updates(self, mock_variant_metric_counter):
        feedback.record("pipe2", "varA", True)
        feedback.record("pipe2", "varA", True)
        feedback.record("pipe2", "varA", False)
        feedback.record("pipe2", "varA", True)
        
        cur = feedback.con.execute("SELECT success, failure FROM ab_stats WHERE pipeline = 'pipe2' AND variant = 'varA'")
        row = cur.fetchone()
        self.assertEqual(row[0], 3) # 3 successes
        self.assertEqual(row[1], 1) # 1 failure

    def test_best_variant_no_data(self):
        self.assertEqual(feedback.best_variant("pipe_empty", default="default_val"), "default_val")

    def test_best_variant_not_enough_trials(self):
        # 19 trials, should use default
        for _ in range(10): feedback.record("pipe_few", "varX", True)
        for _ in range(9): feedback.record("pipe_few", "varX", False)
        self.assertEqual(feedback.best_variant("pipe_few", default="default_X"), "default_X")

        # Add one more trial to varX (now 20 total), it should be chosen
        feedback.record("pipe_few", "varX", True) # 11 success, 9 failure (55%)
        self.assertEqual(feedback.best_variant("pipe_few", default="default_X"), "varX")

    def test_best_variant_selects_highest_rate_sufficient_trials(self):
        # varA: 20 trials, 100% success
        for _ in range(20): feedback.record("pipe_multi", "varA", True)
        # varB: 25 trials, 80% success (20 S, 5 F)
        for _ in range(20): feedback.record("pipe_multi", "varB", True)
        for _ in range(5): feedback.record("pipe_multi", "varB", False)
        # varC: 10 trials, 100% success (not enough trials)
        for _ in range(10): feedback.record("pipe_multi", "varC", True)
        
        self.assertEqual(feedback.best_variant("pipe_multi", default="def"), "varA")

    def test_best_variant_tie_break_by_trials(self):
        # varA: 20 trials, 90% success (18 S, 2 F)
        for _ in range(18): feedback.record("pipe_tie", "varA", True)
        for _ in range(2): feedback.record("pipe_tie", "varA", False)
        # varB: 25 trials, 90% success (22.5 S -> let's make it 23 S, 2 F for integer counts approx 92%)
        # To be precise: 27 trials, 25 success, 2 failure = ~92.5%
        # Let's aim for exact same high rate but different N.
        # varB: 30 trials, 90% success (27 S, 3 F)
        for _ in range(27): feedback.record("pipe_tie", "varB", True)
        for _ in range(3): feedback.record("pipe_tie", "varB", False)

        # Test assumes best_variant has a tie-breaker on N for same rate.
        # The implementation was updated to ORDER BY rate DESC, n DESC
        self.assertEqual(feedback.best_variant("pipe_tie", default="def"), "varB")

    def test_best_variant_default_if_all_variants_low_trials(self):
        for _ in range(5): feedback.record("pipe_all_low", "var1", True)
        for _ in range(10): feedback.record("pipe_all_low", "var2", False)
        self.assertEqual(feedback.best_variant("pipe_all_low", default="default_low"), "default_low")

if __name__ == '__main__':
    unittest.main() 