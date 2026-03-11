from app.models import WordRecord


def test_placeholder() -> None:
    word = WordRecord(
        id=1,
        term="Haus",
        display_prefix="das",
        translation_text="house",
        explanation_text="A building",
        part_of_speech="noun",
        example_source=None,
        example_target=None,
        source="test",
        tags=None,
        difficulty=None,
        times_shown=0,
        last_shown_at=None,
        created_at="",
        updated_at="",
        is_active=1,
    )
    assert word.term == "Haus"
    assert word.display_term == "das Haus"
