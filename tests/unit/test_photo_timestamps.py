from app import format_photo_timestamp


def test_format_photo_timestamp_converts_utc_to_local_timezone():
    formatted = format_photo_timestamp("2026-08-06 13:00:00", tz_name="Europe/Paris")

    assert formatted == "06/08/2026 15:00:00"
