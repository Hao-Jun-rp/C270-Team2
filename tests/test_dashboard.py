"""
Tests for the Admin Dashboard feature (Tristan).
Run all tests:       pytest
Run just this file:  pytest tests\test_dashboard.py -v
"""
from app.dashboard.services import (
    get_summary,
    get_next_booking,
    get_dashboard_data,
)

# Test 1
def test_get_summary_counts_booking_statuses():
    bookings = [
        {"status": "Confirmed"},
        {"status": "Confirmed"},
        {"status": "Pending"},
        {"status": "Completed"},
    ]

    summary = get_summary(bookings)

    assert summary["upcoming"] == 2
    assert summary["pending"] == 1
    assert summary["completed"] == 1
# What this tests
# Booking summary calculations are correct.

# Test 2
def test_get_next_booking_returns_first_confirmed_booking():
    bookings = [
        {"status": "Pending", "service": "Deep Cleaning"},
        {"status": "Confirmed", "service": "Home Cleaning"},
        {"status": "Completed", "service": "Office Cleaning"},
    ]

    booking = get_next_booking(bookings)

    assert booking is not None
    assert booking["status"] == "Confirmed"
    assert booking["service"] == "Home Cleaning"
# What this tests:
# The next confirmed booking is selected correctly.

# Test 3
def test_get_dashboard_data_contains_expected_keys(monkeypatch):
    sample_bookings = [
        {
            "status": "Confirmed",
            "service": "Home Cleaning",
            "date": "13 Jul 2026",
            "time": "10:00 AM",
            "cleaner": "Alice",
            "address": "123 Street",
            "notes": "",
            "price": 100,
            "duration": "2 hours",
        }
    ]
    monkeypatch.setattr(
        "app.dashboard.services.get_bookings",
        lambda: sample_bookings,
    )
    monkeypatch.setattr(
        "app.dashboard.services.get_recent_activity",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.dashboard.services.get_cleaning_tips",
        lambda: ["Tip 1"],
    )
    monkeypatch.setattr(
        "app.dashboard.services.get_latest_review",
        lambda: {},
    )
    dashboard = get_dashboard_data()
    expected_keys = {
        "bookings",
        "summary",
        "next_booking",
        "upcoming_bookings",
        "activities",
        "latest_review",
        "calendar",
        "tips",
        "current_tip",
    }
    assert expected_keys.issubset(dashboard.keys())
# What this test:
# The main dashboard service returns all the data the templates expect.
