import sys
import os
import pytest
from datetime import datetime
import math
import uuid
from hashlib import md5

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from session_calculator import calculate_price, generate_payment_hash, generate_transaction_validation_hash, check_payment_amount

def load_payment_data():
    return []

def test_calculate_price_short_stay():
    parkinglot = {"tariff": 2.0, "daytariff": 10.0}
    sid = "test_sid"
    data = {
        "started": "01-01-2023 10:00:00",
        "stopped": "01-01-2023 10:02:00"
    }
    price, hours, days = calculate_price(parkinglot, sid, data)
    assert price == 0
    assert hours == 1
    assert days == 0

def test_calculate_price_same_day():
    parkinglot = {"tariff": 2.0, "daytariff": 10.0}
    sid = "test_sid"
    data = {
        "started": "01-01-2023 10:00:00",
        "stopped": "01-01-2023 14:00:00"
    }
    price, hours, days = calculate_price(parkinglot, sid, data)
    assert price == 8.0
    assert hours == 4
    assert days == 0

def test_calculate_price_same_day_capped():
    parkinglot = {"tariff": 2.0, "daytariff": 10.0}
    sid = "test_sid"
    data = {
        "started": "01-01-2023 10:00:00",
        "stopped": "01-01-2023 20:00:00"
    }
    price, hours, days = calculate_price(parkinglot, sid, data)
    assert price == 10.0
    assert hours == 10
    assert days == 0

def test_calculate_price_overnight():
    parkinglot = {"tariff": 2.0, "daytariff": 10.0}
    sid = "test_sid"
    data = {
        "started": "01-01-2023 22:00:00",
        "stopped": "02-01-2023 02:00:00"
    }
    price, hours, days = calculate_price(parkinglot, sid, data)
    assert price == 20.0
    assert hours == 4
    assert days == 2

def test_calculate_price_no_stop_time(mocker):
    parkinglot = {"tariff": 2.0, "daytariff": 10.0}
    sid = "test_sid"
    data = {
        "started": "01-01-2023 10:00:00"
    }
    mock_now = mocker.patch('session_calculator.datetime')
    mock_now.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
    mock_now.strptime = datetime.strptime
    price, hours, days = calculate_price(parkinglot, sid, data)
    assert price == 4.0
    assert hours == 2
    assert days == 0

def test_generate_payment_hash():
    sid = "test_sid"
    data = {"licenseplate": "ABC123"}
    expected_hash = md5((sid + data["licenseplate"]).encode("utf-8")).hexdigest()
    assert generate_payment_hash(sid, data) == expected_hash

def test_generate_transaction_validation_hash():
    hash1 = generate_transaction_validation_hash()
    hash2 = generate_transaction_validation_hash()
    assert isinstance(hash1, str)
    assert hash1 != hash2

def test_check_payment_amount(mocker):
    mock_payments = [
        {"transaction": "hash1", "amount": 10.0},
        {"transaction": "hash2", "amount": 20.0},
        {"transaction": "hash1", "amount": 5.0},
        {"transaction": "hash3", "amount": 15.0}
    ]
    mocker.patch('session_calculator.load_payment_data', return_value=mock_payments)
    total = check_payment_amount("hash1")
    assert total == 15.0

def test_check_payment_amount_no_match(mocker):
    mock_payments = [
        {"transaction": "hash2", "amount": 20.0},
        {"transaction": "hash3", "amount": 15.0}
    ]
    mocker.patch('session_calculator.load_payment_data', return_value=mock_payments)
    total = check_payment_amount("hash1")
    assert total == 0