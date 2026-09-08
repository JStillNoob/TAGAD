from collections import defaultdict

from django.utils import timezone

from .models import EngagementSummary


CATEGORIES = ('engaged', 'attentive', 'confused', 'bored', 'disengaged')


def _percentage(count, total):
    return round(count * 100 / total, 1) if total else None


def _session_engagement(session):
    counts = defaultdict(int)
    for summary in EngagementSummary.objects.filter(event__session=session):
        classified = 0
        for category in CATEGORIES:
            count = getattr(summary, f'{category}_count')
            counts[category] += count
            classified += count
        counts['total'] += classified
    return _percentage(counts['engaged'], counts['total'])


def _insight(row, field):
    return {
        'slide_number': row['slide_number'],
        'title': row['title'],
        'percentage': row[field],
    }


def build_session_analytics(session, previous_session=None):
    events = list(
        session.slide_events.select_related('slide')
        .prefetch_related('summaries')
        .order_by('entered_at', 'pk')
    )
    effective_end = session.ended_at or timezone.now()
    rows = {}
    overall_counts = defaultdict(int)
    confidence_weighted_total = 0.0
    students_detected = 0
    total_detections = 0
    unclassified_detections = 0

    for index, event in enumerate(events):
        boundary = events[index + 1].entered_at if index + 1 < len(events) else effective_end
        duration = max(0, round((boundary - event.entered_at).total_seconds()))
        row = rows.setdefault(event.slide_id, {
            'slide_id': event.slide_id,
            'slide_number': event.slide.slide_number,
            'title': event.slide.slide_title or f'Slide {event.slide.slide_number}',
            'entered_at': event.entered_at,
            'duration_seconds': 0,
            'counts': defaultdict(int),
            'total': 0,
            'unclassified': 0,
            'detected': 0,
            'confidence_weighted_total': 0.0,
        })
        row['duration_seconds'] += duration

        for summary in event.summaries.all():
            classified = 0
            for category in CATEGORIES:
                count = getattr(summary, f'{category}_count')
                row['counts'][category] += count
                overall_counts[category] += count
                classified += count
            row['total'] += classified
            overall_counts['total'] += classified
            row['unclassified'] += summary.unclassified_count
            total_detections += summary.total_detected
            unclassified_detections += summary.unclassified_count
            row['detected'] = max(row['detected'], summary.total_detected)
            students_detected = max(students_detected, summary.total_detected)
            weighted_confidence = float(summary.average_confidence) * classified
            row['confidence_weighted_total'] += weighted_confidence
            confidence_weighted_total += weighted_confidence

    slides = []
    for row in sorted(rows.values(), key=lambda item: item['slide_number']):
        total = row.pop('total')
        counts = row.pop('counts')
        weighted_confidence = row.pop('confidence_weighted_total')
        row['entered_at'] = row['entered_at'].isoformat()
        row['has_data'] = bool(total)
        row['average_confidence'] = round(weighted_confidence / total, 1) if total else None
        for category in CATEGORIES:
            row[category] = _percentage(counts[category], total)
        slides.append(row)

    classified_detections = overall_counts['total']
    average_engagement = _percentage(overall_counts['engaged'], classified_detections)
    previous_engagement = _session_engagement(previous_session) if previous_session else None
    engagement_change = (
        round(average_engagement - previous_engagement, 1)
        if average_engagement is not None and previous_engagement is not None
        else None
    )
    duration_seconds = max(0, round((effective_end - session.started_at).total_seconds()))
    data_rows = [row for row in slides if row['has_data']]
    insights = None
    if data_rows:
        highest = max(data_rows, key=lambda row: row['engaged'])
        confused = max(data_rows, key=lambda row: row['confused'])
        disengaged = max(data_rows, key=lambda row: row['disengaged'])
        insights = {
            'highest_engagement': _insight(highest, 'engaged'),
            'most_confusion': _insight(confused, 'confused'),
            'most_disengaged': _insight(disengaged, 'disengaged'),
            'recommendation': (
                f"Review Slide {confused['slide_number']} ({confused['title']}), "
                'where confusion was highest.'
            ),
        }

    return {
        'session': {
            'id': session.pk,
            'subject_code': session.subject.subject_code,
            'subject_name': session.subject.subject_name,
            'classroom': session.subject.classroom.room_code,
            'teacher_name': session.user.get_full_name() or session.user.username,
            'session_date': session.session_date,
            'started_at': session.started_at,
            'ended_at': session.ended_at,
            'status': 'completed' if session.ended_at else 'ongoing',
            'duration_seconds': duration_seconds,
            'slides_covered': len(slides),
        },
        'has_data': bool(classified_detections),
        'summary': {
            'students_detected': students_detected,
            'total_detections': total_detections,
            'classified_detections': classified_detections,
            'unclassified_detections': unclassified_detections,
            'average_engagement': average_engagement,
            'average_confidence': (
                round(confidence_weighted_total / classified_detections, 1)
                if classified_detections else None
            ),
            'engagement_change': engagement_change,
        },
        'distribution': {
            category: _percentage(overall_counts[category], classified_detections) or 0
            for category in CATEGORIES
        },
        'insights': insights,
        'slides': slides,
    }
