

class TestCheckRatioBounds:
    """The single-value bound check (the '900% of quota' case)."""

    def test_valid_shares_pass(self):
        from helpers.data.sql_helpers import check_ratio_bounds
        assert check_ratio_bounds([0.1, 0.4, 0.5])["status"] == "PASS"

    def test_impossible_attainment_fails(self):
        from helpers.data.sql_helpers import check_ratio_bounds
        r = check_ratio_bounds([0.5, 9.0, 0.3], kind="quota attainment")
        assert r["status"] == "FAIL"
        assert "9" in r["message"]
        assert r["details"]["n_above"] == 1

    def test_percent_scale(self):
        from helpers.data.sql_helpers import check_ratio_bounds
        assert check_ratio_bounds([20, 140, 30], lower=0, upper=100)["status"] == "FAIL"
        assert check_ratio_bounds([20, 90, 30], lower=0, upper=100)["status"] == "PASS"

    def test_empty_passes(self):
        from helpers.data.sql_helpers import check_ratio_bounds
        assert check_ratio_bounds([])["status"] == "PASS"
