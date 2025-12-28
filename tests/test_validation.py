from datetime import datetime, timedelta

from models import Showtime
from validation import deduplicate_showtimes, validate_showtime, validate_showtimes


class TestValidateShowtime:
    def test_valid_showtime(self):
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="Test Movie",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
        )
        assert validate_showtime(showtime) is True

    def test_valid_showtime_with_screen_type(self):
        """Test validation of a valid showtime with custom screen_type."""
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="Test Movie",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
            screen_type="IMAX",
        )
        assert validate_showtime(showtime) is True
        assert showtime.screen_type == "IMAX"

    def test_default_screen_type(self):
        """Test that screen_type defaults to 2D."""
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="Test Movie",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
        )
        assert showtime.screen_type == "2D"

    def test_missing_cinema(self):
        showtime = Showtime(
            cinema="",
            location="Test Location",
            title="Test Movie",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
        )
        assert validate_showtime(showtime) is False

    def test_missing_location(self):
        showtime = Showtime(
            cinema="Test Cinema",
            location="",
            title="Test Movie",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
        )
        assert validate_showtime(showtime) is False

    def test_missing_title(self):
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="",
            time="19:00",
            date=datetime.now() + timedelta(days=1),
        )
        assert validate_showtime(showtime) is False

    def test_missing_time(self):
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="Test Movie",
            time="",
            date=datetime.now() + timedelta(days=1),
        )
        assert validate_showtime(showtime) is False

    def test_past_date(self):
        showtime = Showtime(
            cinema="Test Cinema",
            location="Test Location",
            title="Test Movie",
            time="19:00",
            date=datetime.now() - timedelta(days=2),
        )
        assert validate_showtime(showtime) is False


class TestValidateShowtimes:
    def test_filters_invalid_showtimes(self):
        dt = datetime.now() + timedelta(days=1)
        showtimes = [
            Showtime("Cinema 1", "Location 1", "Movie 1", "19:00", dt),
            Showtime("", "Location 2", "Movie 2", "20:00", dt),  # Invalid
            Showtime("Cinema 3", "Location 3", "Movie 3", "21:00", dt),
        ]
        valid = validate_showtimes(showtimes)
        assert len(valid) == 2
        assert valid[0].cinema == "Cinema 1"
        assert valid[1].cinema == "Cinema 3"

    def test_all_valid(self):
        """Test when all showtimes are valid."""
        dt = datetime.now() + timedelta(days=1)
        showtimes = [
            Showtime("Cinema 1", "Location 1", "Movie 1", "19:00", dt),
            Showtime("Cinema 2", "Location 2", "Movie 2", "20:00", dt),
        ]
        valid = validate_showtimes(showtimes)
        assert len(valid) == 2

    def test_all_invalid(self):
        dt = datetime.now() + timedelta(days=1)
        showtimes = [
            Showtime("", "Location 1", "Movie 1", "19:00", dt),
            Showtime("Cinema 2", "", "Movie 2", "20:00", dt),
        ]
        valid = validate_showtimes(showtimes)
        assert len(valid) == 0


class TestDeduplicateShowtimes:
    def test_removes_duplicates_with_date(self):
        dt = datetime.now() + timedelta(days=1)
        showtimes = [
            Showtime("Cinema 1", "Location 1", "Movie 1", "19:00", dt),
            Showtime("Cinema 1", "Location 1", "Movie 1", "19:00", dt),
            Showtime("Cinema 1", "Location 1", "Movie 2", "20:00", dt),
        ]
        unique = deduplicate_showtimes(showtimes)
        assert len(unique) == 2
