"""Tests for movie_cache.py fuzzy matching functionality."""

from movie_cache import MovieCache


class TestMovieCache:
    """Test suite for MovieCache fuzzy matching."""

    def test_exact_match(self):
        """Test exact title match returns correct movie."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Mufasa", "year": 2024},
            2: {"title": "Nosferatu", "year": 2024},
        }

        result = cache.find_match("Mufasa", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Mufasa"
        assert db_year == 2024

    def test_fuzzy_match_with_subtitle(self):
        """Test fuzzy matching handles meaningful subtitles (not screening formats)."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Warlord: Olori Ogun", "year": 2024},
        }

        # Full title should match exactly
        result = cache.find_match("Warlord: Olori Ogun", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Warlord: Olori Ogun"

    def test_fuzzy_match_typo(self):
        """Test fuzzy matching catches typos."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Mufasa", "year": 2024},
        }

        result = cache.find_match("Mufaza", 2024)  # Typo: 'z' instead of 's'
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Mufasa"

    def test_fuzzy_match_punctuation(self):
        """Test fuzzy matching handles punctuation differences."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Spider-Man", "year": 2024},
        }

        result = cache.find_match("Spider Man", 2024)  # Missing hyphen
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Spider-Man"

    def test_fuzzy_match_case_insensitive(self):
        """Test matching is case-insensitive."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "The Lion King", "year": 2024},
        }

        result = cache.find_match("the lion king", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "The Lion King"

    def test_year_preference(self):
        """Test that matching year gives preference."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Nosferatu", "year": 1922},
            2: {"title": "Nosferatu", "year": 2024},
        }

        # Should prefer the 2024 version when searching with year=2024
        result = cache.find_match("Nosferatu", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 2
        assert db_year == 2024

    def test_no_match_below_threshold(self):
        """Test that completely different titles don't match."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Mufasa", "year": 2024},
        }

        result = cache.find_match("Completely Different Movie", 2024)
        assert result is None

    def test_empty_cache(self):
        """Test that empty cache returns None."""
        cache = MovieCache()
        result = cache.find_match("Any Movie", 2024)
        assert result is None

    def test_add_movie(self):
        """Test adding movies to cache."""
        cache = MovieCache()
        cache.add_movie(1, "Mufasa", 2024)

        assert len(cache) == 1
        result = cache.find_match("Mufasa", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1

    def test_add_movie_with_none_year(self):
        """Test adding movie with None year."""
        cache = MovieCache()
        cache.add_movie(1, "Unknown Year Movie", None)

        assert len(cache) == 1
        result = cache.find_match("Unknown Year Movie", None)
        assert result is not None

    def test_multiple_similar_titles_best_match(self):
        """Test that best match is returned when multiple similar titles exist."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Nosferatu", "year": 2024},
            2: {"title": "Nosferatu: A Symphony of Horror", "year": 1922},
        }

        # Exact match should win over subtitle match
        result = cache.find_match("Nosferatu", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1  # Exact match with matching year
        assert db_title == "Nosferatu"

    def test_british_vs_american_spelling(self):
        """Test fuzzy matching handles spelling variants like 'ou' vs 'o'."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Colors of Fire", "year": 2024},
        }

        result = cache.find_match("Colours of Fire", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Colors of Fire"

    def test_find_match_without_year(self):
        """Test matching without providing year."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Timeless Movie", "year": 2020},
        }

        result = cache.find_match("Timeless Movie", None)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1

    def test_colon_prefix_match_warlord(self):
        """Test that 'Warlord' matches 'Warlord: Olori Ogun' via prefix matching."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Warlord: Olori Ogun", "year": 2024},
        }

        result = cache.find_match("Warlord", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Warlord: Olori Ogun"

    def test_colon_prefix_match_agesinkole(self):
        """Test that 'Agesinkole 2' matches 'Agesinkole 2: King of Thieves'."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Agesinkole 2: King of Thieves", "year": 2024},
        }

        result = cache.find_match("Agesinkole 2", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Agesinkole 2: King of Thieves"

    def test_colon_prefix_match_case_insensitive(self):
        """Test prefix matching is case-insensitive."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "AGESHINKOLE 2: King of Thieves", "year": 2024},
        }

        result = cache.find_match("ageshinkole 2", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1

    def test_colon_prefix_match_with_typo(self):
        """Test prefix matching works with typos in base title."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Warlord: Olori Ogun", "year": 2024},
        }

        # "Warlrd" (missing 'o') should still match via fuzzy prefix
        result = cache.find_match("Warlrd", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Warlord: Olori Ogun"

    def test_colon_full_title_still_works(self):
        """Test that full title with subtitle still matches."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Warlord: Olori Ogun", "year": 2024},
        }

        # Searching with full title should still work
        result = cache.find_match("Warlord: Olori Ogun", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1

    def test_colon_no_false_positives(self):
        """Test that prefix matching doesn't create false positives."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Spider-Man: No Way Home", "year": 2021},
            2: {"title": "Spider-Man: Far From Home", "year": 2019},
        }

        # "Spider-Man" alone shouldn't match if there's ambiguity
        # It should match the first one found with best score
        result = cache.find_match("Spider-Man", 2021)
        assert result is not None
        movie_id, db_title, db_year = result
        # Should prefer the one with matching year
        assert movie_id == 1
        assert db_year == 2021

    def test_colon_prefix_vs_exact_match_precedence(self):
        """Test that exact matches still win over prefix matches."""
        cache = MovieCache()
        cache._movies = {
            1: {"title": "Warlord", "year": 2024},
            2: {"title": "Warlord: Olori Ogun", "year": 2024},
        }

        # Searching for "Warlord" should match exact title first
        result = cache.find_match("Warlord", 2024)
        assert result is not None
        movie_id, db_title, db_year = result
        assert movie_id == 1
        assert db_title == "Warlord"
