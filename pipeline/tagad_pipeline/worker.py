import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import cv2

from .artifacts import ArtifactVerificationError, verify_artifacts
from .backend_client import BackendClient, BackendRequestError, build_payload
from .inference import CameraPipeline, ModelBundle, PipelineConfigurationError


PIPELINE_VERSION = 'hierarchical-1'
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / 'backend' / 'model_artifacts'
MANIFEST_PATH = Path(__file__).resolve().parents[1] / 'artifact-manifest.json'


def source_value(raw_source):
    return int(raw_source) if raw_source.isdecimal() else raw_source


def parser():
    result = argparse.ArgumentParser(
        description='Run the TAGAD single-camera engagement pipeline.',
    )
    result.add_argument(
        '--source',
        help='Video path, webcam number, or RTSP URL. Defaults to TAGAD_CAMERA_SOURCE.',
    )
    result.add_argument('--model-dir', type=Path, default=DEFAULT_MODEL_DIR)
    result.add_argument('--session-id', type=int)
    result.add_argument('--backend-url', default='http://127.0.0.1:8000')
    result.add_argument('--dry-run', action='store_true')
    result.add_argument('--preview', action='store_true')
    result.add_argument('--analysis-hz', type=float, default=8.0)
    result.add_argument('--summary-seconds', type=float, default=3.0)
    result.add_argument('--yolo-confidence', type=float, default=0.60)
    result.add_argument('--confirmation-seconds', type=float, default=1.2)
    result.add_argument('--minimum-valid-faces', type=int, default=5)
    result.add_argument('--max-heads', type=int, default=40)
    result.add_argument(
        '--max-analysis-frames', type=int,
        help='Stop after this many analyzed frames (useful for smoke tests).',
    )
    return result


def validate_args(args, cli_parser):
    args.source = args.source or os.environ.get('TAGAD_CAMERA_SOURCE', '')
    if not args.source:
        cli_parser.error('Set --source or the TAGAD_CAMERA_SOURCE environment variable.')
    if args.analysis_hz <= 0:
        cli_parser.error('--analysis-hz must be greater than zero.')
    if args.summary_seconds <= 0:
        cli_parser.error('--summary-seconds must be greater than zero.')
    if not 0 < args.yolo_confidence <= 1:
        cli_parser.error('--yolo-confidence must be between 0 and 1.')
    if args.confirmation_seconds < 0 or args.minimum_valid_faces < 1 or args.max_heads < 1:
        cli_parser.error('Confirmation and capacity values are invalid.')
    if not args.dry_run and not args.session_id:
        cli_parser.error('--session-id is required unless --dry-run is used.')


def model_paths(model_dir):
    return {
        'yolo_path': model_dir / 'tagad_yolo11_head_v2_best.pt',
        'landmarker_path': model_dir / 'face_landmarker.task',
        'state_path': model_dir / 'tagad_state_svm_rich_threshold1_candidate.joblib',
        'attention_path': model_dir / 'dipser_attention_10-feature_diagnostic.joblib',
    }


def display_preview(frame, analysis):
    text = (
        f'candidates={analysis.yolo_candidates} faces={analysis.valid_faces} '
        f'confirmed={analysis.confirmed_students}'
    )
    cv2.putText(frame, text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow('TAGAD pipeline preview - Q to quit', frame)
    return cv2.waitKey(1) & 0xFF == ord('q')


def run(args):
    api_key = os.environ.get('TAGAD_PIPELINE_API_KEY', '')
    if not args.dry_run and not api_key:
        raise PipelineConfigurationError(
            'Set TAGAD_PIPELINE_API_KEY to the same private value as backend PIPELINE_API_KEY.',
        )

    verify_artifacts(args.model_dir, MANIFEST_PATH)
    models = ModelBundle(**model_paths(args.model_dir))
    pipeline = CameraPipeline(
        models,
        yolo_confidence=args.yolo_confidence,
        max_heads=args.max_heads,
        confirmation_seconds=args.confirmation_seconds,
        confirmation_valid_faces=args.minimum_valid_faces,
    )
    capture = cv2.VideoCapture(source_value(args.source))
    if not capture.isOpened():
        models.close()
        raise PipelineConfigurationError('The configured video source could not be opened.')

    client = None if args.dry_run else BackendClient(args.backend_url, api_key)
    fps = capture.get(cv2.CAP_PROP_FPS)
    is_recorded_video = not args.source.isdecimal() and not args.source.lower().startswith(
        ('rtsp://', 'http://', 'https://'),
    )
    if not fps or fps <= 0:
        fps = args.analysis_hz
    frame_step = max(1, round(fps / args.analysis_hz))
    frame_number = 0
    analyzed = 0
    latest_analysis = None
    next_summary_at = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_number += 1
            if frame_number % frame_step:
                continue

            timestamp = frame_number / fps if is_recorded_video else time.monotonic()
            latest_analysis = pipeline.process_frame(frame, timestamp)
            analyzed += 1

            if args.preview and display_preview(frame, latest_analysis):
                break

            clock = timestamp if is_recorded_video else time.monotonic()
            if clock >= next_summary_at:
                metrics = {
                    'yolo_candidates': latest_analysis.yolo_candidates,
                    'valid_faces': latest_analysis.valid_faces,
                    'confirmed_students': latest_analysis.confirmed_students,
                    'states': dict(Counter(
                        prediction['label'] or 'Unclassified'
                        for prediction in latest_analysis.predictions
                    )),
                }
                if args.dry_run:
                    print(json.dumps(metrics), flush=True)
                else:
                    context = client.session_context(args.session_id)
                    if not context['active']:
                        print('Session ended; stopping the pipeline.', flush=True)
                        break
                    slide_event_id = context.get('slide_event_id')
                    if slide_event_id and latest_analysis.predictions:
                        payload = build_payload(
                            session_id=args.session_id,
                            slide_event_id=slide_event_id,
                            predictions=latest_analysis.predictions,
                            pipeline_version=PIPELINE_VERSION,
                        )
                        client.submit(payload)
                        print(json.dumps(metrics), flush=True)
                next_summary_at = clock + args.summary_seconds

            if args.max_analysis_frames and analyzed >= args.max_analysis_frames:
                break
    finally:
        capture.release()
        models.close()
        if args.preview:
            cv2.destroyAllWindows()

    return 0 if analyzed else 2


def main():
    cli_parser = parser()
    args = cli_parser.parse_args()
    validate_args(args, cli_parser)
    try:
        return run(args)
    except (
        ArtifactVerificationError, BackendRequestError, PipelineConfigurationError,
        OSError, ValueError,
    ) as error:
        print(f'Pipeline error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
