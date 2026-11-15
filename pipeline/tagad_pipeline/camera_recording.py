"""Private stream-copy recording for the approved classroom pilot."""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from .configuration import load_configuration


REPO_ROOT = Path(__file__).resolve().parents[2]
MINIMUM_FREE_BYTES = 512 * 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parser():
    result = argparse.ArgumentParser(description='Record the approved Front, Left, and Right beta videos privately.')
    result.add_argument('--config', type=Path, default=REPO_ROOT / 'pipeline' / 'camera_sources.local.json')
    result.add_argument('--output-root', type=Path, default=Path('C:/TAGAD_PRIVATE_PILOT'))
    result.add_argument('--minutes', type=float, default=60)
    result.add_argument('--check', action='store_true', help='Check local readiness without opening camera connections.')
    return result


def validate_inputs(args):
    if not math.isfinite(args.minutes) or not 0 < args.minutes <= 180:
        raise ValueError('Recording duration must be between zero and 180 minutes.')
    args.output_root = args.output_root.resolve()
    if args.output_root.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError('Choose a private recording folder outside the repository.')
    configuration = load_configuration(args.config)
    if sorted(source.position for source in configuration.cameras) != ['front', 'left', 'right']:
        raise ValueError('Configure exactly one Front, Left, and Right camera.')
    for source in configuration.cameras:
        address = urlparse(source.source)
        if source.source_type != 'live' or address.scheme != 'rtsp' or not address.hostname:
            raise ValueError('Recording requires three configured live RTSP sources.')
    existing_parent = args.output_root
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if shutil.disk_usage(existing_parent).free < 2 * 1024 ** 3:
        raise ValueError('At least 2 GiB of free space is required to begin recording.')
    return configuration.cameras


def record_segment(source, destination, deadline, stop, av):
    result = {
        'file': destination.name, 'opened_at_utc': utc_now(),
        'first_packet_at_utc': None, 'last_packet_at_utc': None,
        'packets': 0, 'inferred_dts_packets': 0, 'skipped_packets': 0,
        'irregular_timestamp_intervals': 0, 'timestamp_basis': 'source presentation timestamps',
        'corrected_timestamp_packets': 0, 'tail_estimated_timestamp_packets': 0,
        'max_timestamp_adjustment_seconds': 0.0,
        'status': 'failed', 'error_code': None,
    }
    try:
        with av.open(source.source, timeout=(10, 5), options={'rtsp_transport': 'tcp'}) as incoming:
            if not incoming.streams.video:
                raise ValueError('Video stream unavailable.')
            stream = incoming.streams.video[0]
            if stream.codec_context.name not in {'h264', 'hevc'}:
                raise ValueError('Unsupported camera video codec.')
            result.update({
                'codec': stream.codec_context.name,
                'width': stream.codec_context.width, 'height': stream.codec_context.height,
                'nominal_fps': float(stream.average_rate) if stream.average_rate else None,
            })
            with destination.open('xb') as output_file:
                with av.open(output_file, mode='w', format='mp4', options={
                    'movflags': 'frag_keyframe+empty_moov+default_base_moof',
                    'flush_packets': '1',
                }) as outgoing:
                    output_stream = outgoing.add_stream_from_template(stream)
                    output_stream.time_base = stream.time_base
                    origin, previous_dts = None, None
                    pending, last_frame_step = [], None

                    def write_pending(next_dts=None):
                        nonlocal pending, last_frame_step
                        if not pending:
                            return
                        first_dts = pending[0].dts
                        step = Fraction(next_dts - first_dts, len(pending)) if next_dts is not None else last_frame_step
                        if len(pending) > 1:
                            if step is None and stream.average_rate and pending[0].time_base:
                                step = 1 / (stream.average_rate * pending[0].time_base)
                            if (
                                step is None or step < 1
                                or step * len(pending) * pending[0].time_base > 1
                            ):
                                result['error_code'] = 'timestamp_correction_limit'
                                raise ValueError('Duplicate timestamp group cannot be safely spaced.')
                            result['timestamp_basis'] = 'source presentation timestamps; duplicate times estimated'
                        for index, buffered in enumerate(pending):
                            if index:
                                adjustment = int(index * step)
                                buffered.pts += adjustment
                                buffered.dts += adjustment
                                result['corrected_timestamp_packets'] += 1
                                result['tail_estimated_timestamp_packets'] += int(next_dts is None)
                                result['max_timestamp_adjustment_seconds'] = max(
                                    result['max_timestamp_adjustment_seconds'], float(adjustment * buffered.time_base),
                                )
                            buffered.pts -= origin
                            buffered.dts -= origin
                            buffered.stream = output_stream
                            outgoing.mux(buffered)
                            result['packets'] += 1
                            result['last_packet_at_utc'] = utc_now()
                        if next_dts is not None:
                            last_frame_step = step
                        pending = []

                    next_space_check = 0.0
                    for packet in incoming.demux(stream):
                        now = time.monotonic()
                        if stop.is_set() or now >= deadline:
                            result['status'] = 'stopped' if stop.is_set() else 'completed'
                            break
                        if now >= next_space_check:
                            if shutil.disk_usage(destination.parent).free < MINIMUM_FREE_BYTES:
                                stop.set()
                                result['error_code'] = 'low_disk_space'
                                raise OSError('Recording reserve reached.')
                            next_space_check = now + 5
                        if not packet.size or packet.pts is None:
                            result['skipped_packets'] += 1
                            continue
                        if origin is None and not packet.is_keyframe:
                            result['skipped_packets'] += 1
                            continue
                        if packet.dts is None:
                            packet.dts = packet.pts
                            result['inferred_dts_packets'] += 1
                        if previous_dts is not None and packet.dts < previous_dts:
                            if len(pending) == 1:
                                write_pending()
                            result['error_code'] = 'timestamp_discontinuity'
                            raise ValueError('Camera timestamps changed.')
                        if previous_dts is not None and packet.dts == previous_dts:
                            # Only bound and space equal timestamps on streams without frame reordering.
                            if (
                                len(pending) >= 9 or stream.codec_context.has_b_frames
                                or packet.pts != packet.dts or pending[0].pts != pending[0].dts
                                or packet.time_base != pending[0].time_base
                            ):
                                result['error_code'] = 'timestamp_correction_limit'
                                raise ValueError('Unsupported duplicate timestamp group.')
                            pending.append(packet)
                            continue
                        if previous_dts is not None and stream.average_rate and packet.time_base:
                            # Nominal camera FPS can differ from real frame intervals.
                            interval = float((packet.dts - previous_dts) * packet.time_base)
                            expected = 1 / float(stream.average_rate)
                            if abs(interval - expected) > expected * 0.2:
                                result['irregular_timestamp_intervals'] += 1
                        if origin is None:
                            origin = packet.dts
                            result['first_packet_at_utc'] = utc_now()
                            result['source_first_dts'] = origin
                            result['time_base'] = str(packet.time_base)
                            print(f'{source.position}: receiving video.', flush=True)
                        write_pending(packet.dts)
                        previous_dts = packet.dts
                        pending.append(packet)
                    else:
                        result['error_code'] = 'stream_ended'
                    write_pending()
    except Exception as error:
        result['status'] = 'failed'
        result['error_code'] = result['error_code'] or type(error).__name__
    if not result['packets']:
        result['status'] = 'failed'
        result['error_code'] = result['error_code'] or 'no_video_packets'
    result['closed_at_utc'] = utc_now()
    result['bytes'] = destination.stat().st_size if destination.exists() else 0
    return result


def record_camera(source, folder, deadline, stop, av, retry_limit=3):
    segments = []
    attempt = 1
    while (
        not stop.is_set() and time.monotonic() < deadline
        and (retry_limit is None or attempt <= retry_limit)
    ):
        destination = folder / f'{source.position}-{attempt:02d}.mp4'
        segment = record_segment(source, destination, deadline, stop, av)
        segments.append(segment)
        if segment['status'] != 'failed':
            break
        print(f'{source.position}: recording interrupted; saved part {attempt}.', flush=True)
        if retry_limit is None or attempt < retry_limit:
            stop.wait(min(30, 2 ** min(attempt, 5)))
        attempt += 1
    if not segments or segments[-1]['status'] == 'failed':
        status = 'failed'
    elif len(segments) > 1:
        status = 'completed_with_gaps'
    elif segments[-1]['status'] == 'stopped':
        status = 'stopped'
    else:
        status = 'completed'
    return {'camera': source.position, 'status': status, 'segments': segments}


def write_manifest(path, manifest):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(manifest, output, indent=2, allow_nan=False)
    temporary.replace(path)


def protect_directory(path):
    if os.name != 'nt':
        path.chmod(0o700)
        return
    identity = subprocess.run(
        ['whoami', '/user', '/fo', 'csv', '/nh'],
        capture_output=True, check=True, timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW,
    ).stdout
    match = re.search(rb'S-1-\d+(?:-\d+)+', identity)
    if match is None:
        raise OSError('Current Windows security identity unavailable.')
    sid = match.group().decode('ascii')
    result = subprocess.run([
        'icacls', str(path), '/inheritance:r', '/grant:r',
        f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F',
    ], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Private recording permissions could not be applied.')


def run(args, sources, av, stop_event=None, session=None):
    args.output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if shutil.disk_usage(args.output_root).free < 2 * 1024 ** 3:
        raise OSError('Insufficient free space to begin recording.')
    code = datetime.now(timezone.utc).strftime('PILOT-%Y%m%dT%H%M%SZ-') + uuid4().hex[:8]
    folder = args.output_root / code
    folder.mkdir(mode=0o700)
    protect_directory(folder)
    manifest = {
        'schema_version': 1, 'session_code': code, 'started_at_utc': utc_now(),
        'requested_minutes': args.minutes if stop_event is None else None,
        'duration_control': 'manual_limit' if stop_event is None else 'session_lifecycle',
        'delete_by_utc': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        'permission_confirmation': 'Operator reports signed student and teacher permissions.',
        'audio_recorded': False, 'recording_method': 'compressed video stream copy',
        'synchronization': 'Manual common visual cue and camera clock-offset review required.',
        'status': 'recording',
        'cameras': [{'camera': source.position, 'status': 'starting'} for source in sources],
    }
    if session is not None:
        manifest['session_id'] = session['session_id']
        manifest['classroom_id'] = session.get('classroom_id')
        manifest['session_started_at'] = session.get('started_at')
    manifest_path = folder / 'recording-manifest.json'
    write_manifest(manifest_path, manifest)
    automatic = stop_event is not None
    stop = stop_event if automatic else threading.Event()
    deadline = math.inf if automatic else time.monotonic() + args.minutes * 60
    print(f'Recording into {folder}.', flush=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        try:
            for source in sources:
                futures[source.position] = executor.submit(
                    record_camera, source, folder, deadline, stop, av,
                    None if automatic else 3,
                )
            while not stop.is_set() and not all(future.done() for future in futures.values()):
                time.sleep(0.5)
        except KeyboardInterrupt:
            stop.set()
            print('Closing recording files...', flush=True)
        except Exception as error:
            stop.set()
            manifest['error_code'] = type(error).__name__
        results = []
        for source in sources:
            future = futures.get(source.position)
            try:
                if future is None:
                    raise RuntimeError('Camera worker was not started.')
                results.append(future.result())
            except Exception as error:
                results.append({'camera': source.position, 'status': 'failed', 'error_code': type(error).__name__, 'segments': []})
        manifest['cameras'] = results
    manifest['ended_at_utc'] = utc_now()
    manifest['stop_reason'] = session.get('stop_reason') if session is not None else None
    manifest['status'] = 'partial' if any(
        camera['status'] in {'failed', 'completed_with_gaps'} for camera in results
    ) else ('stopped' if stop.is_set() else 'completed')
    if manifest['status'] == 'stopped' and manifest['stop_reason'] == 'session_ended':
        manifest['status'] = 'completed'
    usable = all(
        camera['status'] in {'completed', 'stopped'}
        and len(camera['segments']) == 1 and camera['segments'][0]['packets']
        for camera in results
    )
    if usable:
        offline = {'analysis_hz': 2.5, 'cameras': [
            {'position': camera['camera'], 'source': camera['segments'][0]['file'],
             'source_type': 'simulated', 'loop': False}
            for camera in results
        ]}
        with (folder / 'offline-sources.json').open('x', encoding='utf-8') as output:
            json.dump(offline, output, indent=2)
    manifest['offline_config_ready'] = usable
    manifest['timing_review_required'] = any(
        segment.get('corrected_timestamp_packets', 0) or segment.get('inferred_dts_packets', 0)
        for camera in results for segment in camera['segments']
    )
    write_manifest(manifest_path, manifest)
    for camera in results:
        print(f"{camera['camera']}: {camera['status']}", flush=True)
    print('Private videos and recording manifest saved.', flush=True)
    return 1 if manifest['status'] == 'partial' else 0


def main():
    args = parser().parse_args()
    try:
        sources = validate_inputs(args)
        import av
        av.logging.set_level(None)
        if args.check:
            print('Recorder ready for three cameras. Local checks passed.')
            return 0
        return run(args, sources, av)
    except Exception as error:
        print(f'Camera recorder failed ({type(error).__name__}). Check configuration, storage, and PyAV installation.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
