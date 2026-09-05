from ui.theme import MAIN_STYLESHEET


def test_stylesheet_has_new_premium_tokens():
    for token in ("StatusChip", "HeroChip", "PlanCard", "PlanPrice",
                  "PlanExtra", "KeyCaption", "KeyField", "BenefitRow"):
        assert token in MAIN_STYLESHEET, f"falta {token} no stylesheet"


def test_stylesheet_removed_old_free_tokens():
    assert "FreeBanner" not in MAIN_STYLESHEET
    assert "FreeBadge" not in MAIN_STYLESHEET


def test_stylesheet_uses_modern_font_fallback_lists():
    assert "Segoe UI Variable Display" in MAIN_STYLESHEET
    assert "Cascadia Code" in MAIN_STYLESHEET
