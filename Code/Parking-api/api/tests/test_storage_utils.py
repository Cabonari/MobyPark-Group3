import pytest
import json
import os
import sys
from unittest.mock import patch, mock_open, call

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import storage_utils


class TestLoadJson:
    def load_json(filename):
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []  # Returns empty list for missing files
        except Exception:
            return []  # Returns empty list for other errors
    """Tests for load_json function with comprehensive edge cases."""
    
    def test_load_json_valid_file(self):
        """Valid JSON file should return correctly parsed data structure."""
        test_data = {"users": [{
        "id": "1",
        "username": "cindy.leenders42",
        "password": "6b37d1ec969838d29cb611deaff50a6b",
        "name": "Cindy Leenders",
        "email": "cindyleenders@upcmail.nl",
        "phone": "+310792215694",
        "role": "USER",
        "created_at": "2017-10-06",
        "birth_year": 1937,
        "active": True}]}
        json_content = json.dumps(test_data)
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            with patch("os.makedirs") as mock_makedirs:
                result = storage_utils.load_json("test.json")
                assert result == test_data
        
    def test_load_json_empty_file(self):
        """Empty JSON file should return empty structure."""
        empty_json = "{}"
        
        with patch("builtins.open", mock_open(read_data=empty_json)):
            with patch("os.makedirs") as mock_makedirs:
                result = storage_utils.load_json("empty.json")
                assert result == {}

    def test_load_json_file_not_found(self):
        """FileNotFoundError should return empty list as fallback."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("os.makedirs") as mock_makedirs:
                result = storage_utils.load_json("nonexistent.json")
        
        assert result == []

    def test_load_json_invalid_json(self):
        """Malformed JSON content should raise JSONDecodeError."""
        invalid_json = "{'invalid': json}"  # Single quotes break JSON parsing
        
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch("os.makedirs") as mock_makedirs:
                with pytest.raises(json.JSONDecodeError):
                    storage_utils.load_json("invalid.json")


class TestWriteJson:
    """Tests for write_json function with comprehensive scenarios."""
    
    def test_write_json_valid_data(self):
        """Valid data structure should be serialized and written to file in write mode."""
        test_data = {"users": [{"id": 1, "name": "John"}]}
        mock_file = mock_open()
        
        with patch("builtins.open", mock_file):
            storage_utils.write_json("test.json", test_data)
        
        mock_file.assert_called_once_with("test.json", "w")
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        assert json.loads(written_content) == test_data
    
    def test_write_json_permission_error(self):
        """Write permission denied should propagate PermissionError to caller."""
        test_data = {"test": "data"}
        
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                storage_utils.write_json("protected.json", test_data)
    
    def test_write_json_with_datetime_objects(self):
        """Datetime objects should serialize using default=str parameter in json.dump."""
        from datetime import datetime
        test_data = {"created": datetime(2023, 1, 1, 12, 0, 0)}
        mock_file = mock_open()
        
        with patch("builtins.open", mock_file):
            storage_utils.write_json("datetime.json", test_data)
        
        mock_file.assert_called_once_with("datetime.json", "w")
        # Ensure JSON serialization succeeded with datetime objects (requires default=str)
        written_calls = mock_file().write.call_args_list
        assert len(written_calls) > 0


class TestLoadCsv:
    """Tests for load_csv function."""
    
    def test_load_csv_valid_file(self):
        """Valid CSV content should return parsed rows as list of string arrays."""
        csv_content = "name,age,city\nJohn,25,NYC\nJane,30,LA"
        
        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = storage_utils.load_csv("test.csv")
        
        expected = [["name", "age", "city"], ["John", "25", "NYC"], ["Jane", "30", "LA"]]
        assert result == expected
    
    def test_load_csv_empty_file(self):
        """Empty CSV file should return empty list."""
        empty_content = ""
        
        with patch("builtins.open", mock_open(read_data=empty_content)):
            result = storage_utils.load_csv("empty.csv")
        
        assert result == []
    
    def test_load_csv_file_not_found(self):
        """Missing CSV file should return empty list as fallback."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = storage_utils.load_csv("nonexistent.csv")
        
        assert result == []


class TestWriteCsv:
    """Test for write_csv function."""
    
    def test_write_csv_valid_data(self):
        """2D string array should be written as CSV with proper newline handling."""
        test_data = [["name", "age"], ["John", "25"], ["Jane", "30"]]
        mock_file = mock_open()
        
        with patch("builtins.open", mock_file):
            storage_utils.write_csv("test.csv", test_data)
        
        mock_file.assert_called_once_with("test.csv", "w", newline="")
        assert mock_file().write.called  # CSV writer should have written something


class TestLoadText:
    """Tests for load_text function."""
    
    def test_load_text_valid_file(self):
        """Text file should return lines as list with preserved newline characters."""
        text_content = "Line 1\nLine 2\nLine 3"
        
        with patch("builtins.open", mock_open(read_data=text_content)):
            result = storage_utils.load_text("test.txt")
        
        expected = ["Line 1\n", "Line 2\n", "Line 3"]
        assert result == expected
    
    def test_load_text_empty_file(self):
        """Empty text file should return empty list."""
        empty_content = ""
        
        with patch("builtins.open", mock_open(read_data=empty_content)):
            result = storage_utils.load_text("empty.txt")
        
        assert result == []
    
    def test_load_text_file_not_found(self):
        """Missing text file should return empty list as fallback."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = storage_utils.load_text("nonexistent.txt")
        
        assert result == []
    
    def test_load_text_single_line_no_newline(self):
        """Single line without newline should be handled correctly."""
        text_content = "Single line without newline"
        
        with patch("builtins.open", mock_open(read_data=text_content)):
            result = storage_utils.load_text("single.txt")
        
        assert result == ["Single line without newline"]
    
    def test_load_text_with_unicode_characters(self):
        """Multilingual text (Chinese, Arabic, Greek) should load without encoding issues."""
        text_content = "Hello 世界\nمرحبا بالعالم\nΓεια σας κόσμε"
        
        with patch("builtins.open", mock_open(read_data=text_content)):
            result = storage_utils.load_text("unicode.txt")
        
        expected = ["Hello 世界\n", "مرحبا بالعالم\n", "Γεια σας κόσμε"]
        assert result == expected


class TestWriteText:
    """Tests for write_text function."""
    
    def test_write_text_valid_data(self):
        """String list should be written as lines with automatic newline appending."""
        test_data = ["Line 1", "Line 2", "Line 3"]
        mock_file = mock_open()
        
        with patch("builtins.open", mock_file):
            storage_utils.write_text("test.txt", test_data)
        
        mock_file.assert_called_once_with("test.txt", "w")
        expected_calls = [call("Line 1\n"), call("Line 2\n"), call("Line 3\n")]
        mock_file().write.assert_has_calls(expected_calls)
    
    def test_write_text_empty_data(self):
        """Empty string list should create empty text file without any writes."""
        empty_data = []
        mock_file = mock_open()
        
        with patch("builtins.open", mock_file):
            storage_utils.write_text("empty.txt", empty_data)
        
        mock_file.assert_called_once_with("empty.txt", "w")
        mock_file().write.assert_not_called()
    

class TestSaveData:
    """Tests for save_data function with file format detection."""
    
    @patch('storage_utils.write_json')
    def test_save_data_json_format(self, mock_write_json):
        """File extension .json should route to write_json function."""
        test_data = {"test": "data"}
        
        storage_utils.save_data("test.json", test_data)
        
        mock_write_json.assert_called_once_with("test.json", test_data)
    
    @patch('storage_utils.write_csv')
    def test_save_data_csv_format(self, mock_write_csv):
        """CSV filename should call write_csv."""
        test_data = [["header"], ["row1"]]
        
        storage_utils.save_data("test.csv", test_data)
        
        mock_write_csv.assert_called_once_with("test.csv", test_data)
    
    @patch('storage_utils.write_text')
    def test_save_data_text_format(self, mock_write_text):
        """TXT filename should call write_text."""
        test_data = ["line1", "line2"]
        
        storage_utils.save_data("test.txt", test_data)
        
        mock_write_text.assert_called_once_with("test.txt", test_data)
    
    def test_save_data_unsupported_format(self):
        """Unsupported file extension should raise ValueError."""
        test_data = ["some", "data"]
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            storage_utils.save_data("test.xyz", test_data)
    
    @pytest.mark.parametrize("filename,expected_error", [
        ("", ValueError),
        ("noextension", ValueError),
        ("multiple.dots.unknown", ValueError),
    ])
    def test_save_data_edge_case_filenames(self, filename, expected_error):
        """Edge case filenames should be handled appropriately."""
        with pytest.raises(expected_error):
            storage_utils.save_data(filename, [])


class TestLoadData:
    """Tests for load_data function with file format detection."""
    
    @patch('storage_utils.load_json')
    def test_load_data_json_format(self, mock_load_json):
        """JSON filename should call load_json."""
        mock_load_json.return_value = {"test": "data"}
        
        result = storage_utils.load_data("test.json")
        
        mock_load_json.assert_called_once_with("test.json")
        assert result == {"test": "data"}
    
    @patch('storage_utils.load_csv')
    def test_load_data_csv_format(self, mock_load_csv):
        """CSV filename should call load_csv."""
        mock_load_csv.return_value = [["header"], ["row1"]]
        
        result = storage_utils.load_data("test.csv")
        
        mock_load_csv.assert_called_once_with("test.csv")
        assert result == [["header"], ["row1"]]
    
    @patch('storage_utils.load_text')
    def test_load_data_text_format(self, mock_load_text):
        """TXT filename should call load_text."""
        mock_load_text.return_value = ["line1\n", "line2\n"]
        
        result = storage_utils.load_data("test.txt")
        
        mock_load_text.assert_called_once_with("test.txt")
        assert result == ["line1\n", "line2\n"]
    
    def test_load_data_unsupported_format(self):
        """Unsupported file extension should return None."""
        result = storage_utils.load_data("test.xyz")
        
        assert result is None
    
    @pytest.mark.parametrize("filename,expected_result", [
        ("", None),
        ("noextension", None),
        ("multiple.dots.unknown", None),
    ])
    def test_load_data_edge_case_filenames(self, filename, expected_result):
        """Edge case filenames should return None."""
        result = storage_utils.load_data(filename)
        
        assert result == expected_result


class TestSpecificDataFunctions:
    """Tests for specific data loading/saving functions."""
    
    @patch('storage_utils.load_data')
    def test_load_user_data(self, mock_load_data):
        """load_user_data should delegate to load_data with hardcoded users.json path."""
        expected_data = [{"id": 1, "name": "John"}]
        mock_load_data.return_value = expected_data
        
        result = storage_utils.load_user_data()
        
        mock_load_data.assert_called_once_with('data/users.json')
        assert result == expected_data
    
    @patch('storage_utils.save_data')
    def test_save_user_data(self, mock_save_data):
        """save_user_data should delegate to save_data with hardcoded users.json path."""
        test_data = [{"id": 1, "name": "John"}]
        
        storage_utils.save_user_data(test_data)
        
        mock_save_data.assert_called_once_with('data/users.json', test_data)
    
    @patch('storage_utils.load_data')
    def test_load_parking_lot_data(self, mock_load_data):
        """load_parking_lot_data should use hardcoded parking-lots.json path."""
        storage_utils.load_parking_lot_data()
        
        mock_load_data.assert_called_once_with('data/parking-lots.json')
    
    @patch('storage_utils.save_data')
    def test_save_parking_lot_data(self, mock_save_data):
        """save_parking_lot_data should call save_data with correct path."""
        test_data = [{"id": 1, "name": "Lot A"}]
        
        storage_utils.save_parking_lot_data(test_data)
        
        mock_save_data.assert_called_once_with('data/parking-lots.json', test_data)
    
    @patch('storage_utils.load_data')
    def test_load_reservation_data(self, mock_load_data):
        """load_reservation_data should call load_data with correct path."""
        storage_utils.load_reservation_data()
        
        mock_load_data.assert_called_once_with('data/reservations.json')
    
    @patch('storage_utils.save_data')
    def test_save_reservation_data(self, mock_save_data):
        """save_reservation_data should call save_data with correct path."""
        test_data = [{"id": 1, "user_id": 1}]
        
        storage_utils.save_reservation_data(test_data)
        
        mock_save_data.assert_called_once_with('data/reservations.json', test_data)
    
    @patch('storage_utils.load_data')
    def test_load_payment_data(self, mock_load_data):
        """load_payment_data should call load_data with correct path."""
        storage_utils.load_payment_data()
        
        mock_load_data.assert_called_once_with('data/payments.json')
    
    @patch('storage_utils.save_data')
    def test_save_payment_data(self, mock_save_data):
        """save_payment_data should call save_data with correct path."""
        test_data = [{"id": 1, "amount": 10.50}]
        
        storage_utils.save_payment_data(test_data)
        
        mock_save_data.assert_called_once_with('data/payments.json', test_data)
    
    @patch('storage_utils.load_data')
    def test_load_discounts_data(self, mock_load_data):
        """load_discounts_data should call load_data with correct CSV path."""
        storage_utils.load_discounts_data()
        
        mock_load_data.assert_called_once_with('data/discounts.csv')
    
    @patch('storage_utils.save_data')
    def test_save_discounts_data(self, mock_save_data):
        """save_discounts_data should call save_data with correct CSV path."""
        test_data = [["code", "percent"], ["SAVE10", "10"]]
        
        storage_utils.save_discounts_data(test_data)
        
        mock_save_data.assert_called_once_with('data/discounts.csv', test_data)



