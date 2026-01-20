"""Tests for movie_normalizer.py screening format stripping."""

from movie_normalizer import strip_screening_format


class TestStripScreeningFormat:
    """Test suite for strip_screening_format function."""

    def test_strip_vip_suffix(self):
        """Test stripping ': VIP' suffix."""
        assert strip_screening_format("Colors of Fire: VIP") == "Colors of Fire"

    def test_strip_imax_suffix(self):
        """Test stripping ': IMAX' suffix."""
        assert strip_screening_format("Mufasa: IMAX") == "Mufasa"

    def test_strip_3d_suffix(self):
        """Test stripping ': 3D' suffix."""
        assert strip_screening_format("Avatar: 3D") == "Avatar"

    def test_strip_4dx_suffix(self):
        """Test stripping ': 4DX' suffix."""
        assert strip_screening_format("Wicked: 4DX") == "Wicked"

    def test_strip_imax_3d_combined(self):
        """Test stripping combined ': IMAX 3D' suffix."""
        assert strip_screening_format("Mufasa: IMAX 3D") == "Mufasa"

    def test_strip_4dx_3d_combined(self):
        """Test stripping combined ': 4DX 3D' suffix."""
        assert strip_screening_format("Sonic 3: 4DX 3D") == "Sonic 3"

    def test_preserve_meaningful_subtitle(self):
        """Test that meaningful subtitles are preserved."""
        assert strip_screening_format("Warlord: Olori Ogun") == "Warlord: Olori Ogun"

    def test_preserve_meaningful_subtitle_with_number(self):
        """Test that numbered sequels with subtitles are preserved."""
        assert (
            strip_screening_format("Agesinkole 2: King of Thieves")
            == "Agesinkole 2: King of Thieves"
        )

    def test_case_insensitive_vip(self):
        """Test case-insensitive matching for VIP."""
        assert strip_screening_format("Movie: vip") == "Movie"
        assert strip_screening_format("Movie: VIP") == "Movie"
        assert strip_screening_format("Movie: Vip") == "Movie"

    def test_case_insensitive_imax(self):
        """Test case-insensitive matching for IMAX."""
        assert strip_screening_format("Movie: imax") == "Movie"
        assert strip_screening_format("Movie: IMAX") == "Movie"

    def test_whitespace_handling(self):
        """Test handling of various whitespace patterns."""
        assert strip_screening_format("Movie:VIP") == "Movie"
        assert strip_screening_format("Movie: VIP") == "Movie"
        assert strip_screening_format("Movie:  VIP") == "Movie"

    def test_no_change_for_regular_title(self):
        """Test that regular titles without format suffixes are unchanged."""
        assert strip_screening_format("Mufasa") == "Mufasa"
        assert strip_screening_format("The Lion King") == "The Lion King"

    def test_preserve_vip_in_middle_of_title(self):
        """Test that VIP in the middle of a title is preserved."""
        # This is unlikely but ensures word boundary matching works
        assert (
            strip_screening_format("The VIP Lounge: A Story")
            == "The VIP Lounge: A Story"
        )

    def test_multiple_colons_only_strips_format(self):
        """Test handling titles with multiple colons."""
        # Only strips the format suffix, not other colons
        assert strip_screening_format("Movie: Part 1: VIP") == "Movie: Part 1"

    def test_title_with_number_and_colon(self):
        """Test titles with numbers like 'Sonic 3' don't get confused."""
        assert strip_screening_format("Sonic 3: VIP") == "Sonic 3"
        assert strip_screening_format("Sonic 3: IMAX") == "Sonic 3"
