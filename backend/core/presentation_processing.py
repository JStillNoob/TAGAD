import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile

from .models import Presentation, PresentationSlide


class PresentationProcessingError(Exception):
    pass


def _find_libreoffice():
    configured = getattr(settings, 'LIBREOFFICE_PATH', '')
    candidates = [
        configured,
        shutil.which('soffice'),
        shutil.which('libreoffice'),
        r'C:\Program Files\LibreOffice\program\soffice.exe',
        r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
    ]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def _convert_with_libreoffice(executable, source, destination):
    result = subprocess.run(
        [
            executable,
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            str(destination.parent),
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    generated = destination.parent / f'{source.stem}.pdf'
    if result.returncode != 0 or not generated.exists():
        message = result.stderr.strip() or result.stdout.strip() or 'LibreOffice conversion failed.'
        raise PresentationProcessingError(message)
    if generated != destination:
        generated.replace(destination)


def _convert_with_powerpoint(source, destination):
    try:
        import pythoncom
        import win32com.client
    except ImportError as error:
        raise PresentationProcessingError(
            'PPTX conversion requires LibreOffice or Microsoft PowerPoint.',
        ) from error

    application = None
    opened = None
    pythoncom.CoInitialize()
    try:
        application = win32com.client.DispatchEx('PowerPoint.Application')
        opened = application.Presentations.Open(
            str(source.resolve()),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        opened.SaveAs(str(destination.resolve()), 32)
    except Exception as error:
        raise PresentationProcessingError('Microsoft PowerPoint could not convert this file.') from error
    finally:
        if opened is not None:
            opened.Close()
        if application is not None:
            application.Quit()
        pythoncom.CoUninitialize()

    if not destination.exists() or destination.stat().st_size == 0:
        raise PresentationProcessingError('Microsoft PowerPoint did not produce a PDF file.')


def _convert_pptx_to_pdf(source, destination):
    libreoffice = _find_libreoffice()
    if libreoffice:
        _convert_with_libreoffice(libreoffice, source, destination)
        return
    if os.name == 'nt':
        _convert_with_powerpoint(source, destination)
        return
    raise PresentationProcessingError(
        'PPTX conversion requires LibreOffice on this server.',
    )


def _render_pdf(presentation, pdf_path):
    document = pymupdf.open(pdf_path)
    try:
        if document.page_count == 0:
            raise PresentationProcessingError('The presentation does not contain any pages.')
        maximum_slides = getattr(settings, 'PRESENTATION_MAX_SLIDES', 300)
        if document.page_count > maximum_slides:
            raise PresentationProcessingError(
                f'The presentation exceeds the {maximum_slides}-slide limit.',
            )
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            slide = PresentationSlide.objects.create(
                presentation=presentation,
                slide_number=index,
                slide_title=f'Slide {index}',
            )
            slide.image_path.save(
                f'slide-{index}.png',
                ContentFile(pixmap.tobytes('png')),
                save=True,
            )
        return document.page_count
    finally:
        document.close()


def _clear_generated_files(presentation):
    for slide in presentation.slides.all():
        if slide.image_path:
            slide.image_path.delete(save=False)
    presentation.slides.all().delete()
    if presentation.preview_path:
        presentation.preview_path.delete(save=False)
        presentation.preview_path = ''


def process_presentation(presentation):
    presentation.processing_status = Presentation.ProcessingStatus.PROCESSING
    presentation.processing_error = ''
    presentation.save(update_fields=['processing_status', 'processing_error'])
    _clear_generated_files(presentation)

    try:
        with tempfile.TemporaryDirectory() as directory:
            temporary_directory = Path(directory)
            source_path = temporary_directory / f'source.{presentation.file_type}'
            with presentation.file_path.open('rb') as stored_file:
                source_path.write_bytes(stored_file.read())

            if presentation.file_type == Presentation.FileType.PPTX:
                pdf_path = temporary_directory / 'preview.pdf'
                _convert_pptx_to_pdf(source_path, pdf_path)
                with pdf_path.open('rb') as converted_file:
                    presentation.preview_path.save(
                        'preview.pdf',
                        File(converted_file),
                        save=False,
                    )
            else:
                pdf_path = source_path

            presentation.total_slides = _render_pdf(presentation, pdf_path)
            presentation.processing_status = Presentation.ProcessingStatus.READY
            presentation.processing_error = ''
            presentation.save(update_fields=[
                'preview_path',
                'total_slides',
                'processing_status',
                'processing_error',
            ])
    except Exception as error:
        _clear_generated_files(presentation)
        presentation.total_slides = 0
        presentation.processing_status = Presentation.ProcessingStatus.FAILED
        presentation.processing_error = str(error)[:1000] or 'Presentation conversion failed.'
        presentation.save(update_fields=[
            'preview_path',
            'total_slides',
            'processing_status',
            'processing_error',
        ])

    return presentation
