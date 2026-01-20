from datetime import date, datetime

from providers.utils import parse_time_to_datetime


class TestParseTimeToDatetime:
    def test_parse_12hour_with_minutes(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("7:30pm", test_date)
        assert result == datetime(2024, 1, 15, 19, 30)

    def test_parse_12hour_without_minutes(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("7pm", test_date)
        assert result == datetime(2024, 1, 15, 19, 0)

    def test_parse_24hour(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("19:30", test_date)
        assert result == datetime(2024, 1, 15, 19, 30)

    def test_parse_with_spaces(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("7:30 PM", test_date)
        assert result == datetime(2024, 1, 15, 19, 30)

    def test_parse_with_dots(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("7.30pm", test_date)
        assert result == datetime(2024, 1, 15, 19, 30)

    def test_parse_uppercase(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("7:30PM", test_date)
        assert result == datetime(2024, 1, 15, 19, 30)

    def test_parse_am(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("10:00am", test_date)
        assert result == datetime(2024, 1, 15, 10, 0)

    def test_parse_noon(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("12:00pm", test_date)
        assert result == datetime(2024, 1, 15, 12, 0)

    def test_parse_midnight(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("12:00am", test_date)
        assert result == datetime(2024, 1, 15, 0, 0)

    def test_default_to_today(self):
        result = parse_time_to_datetime("7:30pm")
        assert result is not None
        assert result.hour == 19
        assert result.minute == 30
        assert result.date() == datetime.today().date()

    def test_invalid_time_returns_none(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("invalid", test_date)
        assert result is None

    def test_empty_string_returns_none(self):
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("", test_date)
        assert result is None

    def test_parse_typo_ppm(self):
        """Test parsing time with PPM typo (should be PM)."""
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("3:20PPM", test_date)
        assert result == datetime(2024, 1, 15, 15, 20)

    def test_parse_typo_aam(self):
        """Test parsing time with AAM typo (should be AM)."""
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("10:30AAM", test_date)
        assert result == datetime(2024, 1, 15, 10, 30)

    def test_parse_typo_ppm_uppercase(self):
        """Test parsing time with uppercase PPM typo."""
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("3:20PPM", test_date)
        assert result == datetime(2024, 1, 15, 15, 20)

    def test_parse_typo_with_spaces(self):
        """Test parsing time with PPM typo and spaces."""
        test_date = date(2024, 1, 15)
        result = parse_time_to_datetime("3:20 PPM", test_date)
        assert result == datetime(2024, 1, 15, 15, 20)
