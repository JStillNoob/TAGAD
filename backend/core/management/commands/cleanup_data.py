from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import EngagementSummary, Presentation, PresentationSlide, Report, SystemLog


class Command(BaseCommand):
    help = 'Report or delete expired TAGAD data according to the configured retention policy.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Delete the reported records. Without this flag, no data is changed.',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        retention_values = {
            'RETENTION_FAILED_PRESENTATION_DAYS': settings.RETENTION_FAILED_PRESENTATION_DAYS,
            'RETENTION_REPORT_DAYS': settings.RETENTION_REPORT_DAYS,
            'RETENTION_ENGAGEMENT_SUMMARY_DAYS': settings.RETENTION_ENGAGEMENT_SUMMARY_DAYS,
            'RETENTION_SYSTEM_LOG_DAYS': settings.RETENTION_SYSTEM_LOG_DAYS,
        }
        invalid = [name for name, value in retention_values.items() if value < 0]
        if invalid:
            raise CommandError(f'Retention days cannot be negative: {", ".join(invalid)}')
        targets = {
            'failed presentations': Presentation.objects.filter(
                processing_status=Presentation.ProcessingStatus.FAILED,
                uploaded_at__lt=now - timedelta(
                    days=settings.RETENTION_FAILED_PRESENTATION_DAYS,
                ),
                sessions__isnull=True,
                slides__slide_events__isnull=True,
            ).distinct().order_by('pk'),
            'reports': Report.objects.filter(
                generated_at__lt=now - timedelta(days=settings.RETENTION_REPORT_DAYS),
            ).order_by('pk'),
            'engagement summaries': EngagementSummary.objects.filter(
                captured_at__lt=now - timedelta(
                    days=settings.RETENTION_ENGAGEMENT_SUMMARY_DAYS,
                ),
            ).order_by('pk'),
            'system logs': SystemLog.objects.filter(
                logged_at__lt=now - timedelta(days=settings.RETENTION_SYSTEM_LOG_DAYS),
            ).order_by('pk'),
        }
        target_ids = {
            label: list(queryset.values_list('pk', flat=True))
            for label, queryset in targets.items()
        }

        mode = 'EXECUTE' if options['execute'] else 'DRY RUN'
        self.stdout.write(f'{mode}: data lifecycle cleanup at {now.isoformat()}')
        for label, ids in target_ids.items():
            rendered = ', '.join(str(pk) for pk in ids) if ids else 'none'
            self.stdout.write(f'{label} ({len(ids)}): {rendered}')

        if not options['execute']:
            self.stdout.write('No records or files were deleted.')
            return

        reports = list(Report.objects.filter(pk__in=target_ids['reports']))
        stored_presentation_files = []

        with transaction.atomic():
            for presentation_id in target_ids['failed presentations']:
                # Recheck the protection condition while locked before touching files.
                locked = Presentation.objects.select_for_update().get(pk=presentation_id)
                if locked.sessions.exists() or locked.slides.filter(
                    slide_events__isnull=False,
                ).exists():
                    continue
                for slide in locked.slides.all():
                    if slide.image_path:
                        stored_presentation_files.append((
                            slide.image_path.storage,
                            slide.image_path.name,
                            PresentationSlide,
                            'image_path',
                        ))
                for field_name in ('file_path', 'preview_path'):
                    field = getattr(locked, field_name)
                    if field:
                        stored_presentation_files.append((
                            field.storage,
                            field.name,
                            Presentation,
                            field_name,
                        ))
                locked.delete()
            Report.objects.filter(pk__in=target_ids['reports']).delete()
            EngagementSummary.objects.filter(
                pk__in=target_ids['engagement summaries'],
            ).delete()
            SystemLog.objects.filter(pk__in=target_ids['system logs']).delete()

        for storage, path, model, field_name in stored_presentation_files:
            if not model.objects.filter(**{field_name: path}).exists():
                storage.delete(path)
        for report in reports:
            if report.report_path and not Report.objects.filter(
                report_path=report.report_path,
            ).exists():
                default_storage.delete(report.report_path)
        self.stdout.write(self.style.SUCCESS('Cleanup completed.'))
