from datetime import datetime, timezone

import pytest

from app.adapters.secondary.notifications import email_notification_adapter as module
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.events.operation_events import FestivalPublishedEvent, FestivalUnpublishedEvent
from app.domain.value_objects.time_slot import TimeSlot

NOW = datetime(2027, 6, 18, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def sent_emails(monkeypatch):
    emails = []
    monkeypatch.setattr(module, "send_email", lambda **email: emails.append(email))
    return emails


def test_festival_publication_email_names_the_festival_not_a_concert(sent_emails):
    EmailNotificationAdapter().notify_festival_published(
        FestivalPublishedEvent(festival_id=1, festival_name="Hellforge", published_at=NOW)
    )

    [email] = sent_emails
    assert email["subject"] == "Publication du festival #1"
    assert "Hellforge" in email["body"]


def test_festival_unpublication_email_names_the_festival(sent_emails):
    EmailNotificationAdapter().notify_festival_unpublished(
        FestivalUnpublishedEvent(festival_id=1, festival_name="Hellforge", unpublished_at=NOW)
    )

    [email] = sent_emails
    assert email["subject"] == "Retrait du planning du festival #1"
    assert "Hellforge" in email["body"]


def test_concert_rescheduled_email_describes_the_move(sent_emails):
    EmailNotificationAdapter().notify_concert_rescheduled(
        ConcertRescheduledEvent(
            concert_id=5,
            festival_id=1,
            previous_time_slot=TimeSlot(datetime(2027, 6, 19, 10), datetime(2027, 6, 19, 11)),
            new_time_slot=TimeSlot(datetime(2027, 6, 19, 14), datetime(2027, 6, 19, 15)),
            occurred_at=NOW,
        )
    )

    [email] = sent_emails
    assert email["subject"] == "Modification du concert #5"
    assert email["body"] == "Le concert a été déplacé du 2027-06-19T10:00:00 au 2027-06-19T14:00:00"
