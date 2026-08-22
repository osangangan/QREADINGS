from qreadings_ai.trajectory import parse_translation_history


def test_translation_history_parses_entry_types_and_notes():
    text = """
QReading Day 5

Chapter 6 Verse 54 of the Qur'an

When those who believe in Our signs come to you.

QUR’ANIC WORD OF THE DAY

Ayat = signs.

NOTE ON TRANSLATION

The word ayat is translated here as signs.

SPECIAL READING 1

Chapter 20 Verses 25–28 of the Qur'an

My Sustainer, expand for me my chest.
"""
    versions = parse_translation_history(text, source_path="365 Days of Q.txt")

    assert len(versions) == 2
    assert versions[0].entry_type == "qreading_day"
    assert versions[0].day_number == 5
    assert versions[0].reference == "Chapter 6 Verse 54 of the Qur'an"
    assert versions[0].trajectory_key == "6:54"
    assert versions[0].word_of_day == "Ayat = signs."
    assert versions[0].translation_note == "The word ayat is translated here as signs."
    assert versions[1].entry_type == "special_reading"


def test_possible_readings_is_supported():
    text = """
POSSIBLE READINGS 01

Chapter 19 Verses 23–25

Then the ford brought her to the palm trunk.
"""
    versions = parse_translation_history(text)
    assert len(versions) == 1
    assert versions[0].entry_type == "possible_readings"
    assert versions[0].trajectory_key == "19:23–25"
