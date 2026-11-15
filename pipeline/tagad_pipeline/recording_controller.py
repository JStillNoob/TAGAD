"""Standby recorder driven by authenticated TAGAD session lifecycle updates."""

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from .backend_client import BackendClient, BackendRequestError
from .camera_recording import REPO_ROOT, run, validate_inputs
from .configuration import load_configuration


class SessionRecording(threading.Thread):
    def __init__(self, session, sources, args, av):
        super().__init__(name=f"session-recorder-{session['session_id']}")
        self.session = {
            key: session.get(key)
            for key in ('session_id', 'classroom_id', 'started_at')
        }
        self.sources, self.args, self.av = sources, args, av
        self.stop_event = threading.Event()
        self.exit_status = None

    def stop(self, reason):
        self.session.setdefault('stop_reason', reason)
        self.stop_event.set()

    def run(self):
        try:
            self.exit_status = run(self.args, self.sources, self.av, self.stop_event, self.session)
        except Exception as error:
            self.exit_status = 1
            print(f'Session recorder failed ({type(error).__name__}).', file=sys.stderr, flush=True)


class RecordingController:
    def __init__(self, client, configuration, args, av, job_factory=SessionRecording):
        self.client, self.configuration = client, configuration
        self.args, self.av, self.job_factory = args, av, job_factory
        # shortcut: one local pilot session at a time, extend for concurrent classroom stations.
        self.job = None
        self.finished = set()
        self.retry_after = {}

    def sources_for(self, session):
        sources = []
        for camera in session.get('cameras', []):
            if not camera.get('ip_address'):
                return ()
            source = self.configuration.source_for(camera)
            if source is None or source.source_type != 'live' or source.position != camera.get('position'):
                return ()
            sources.append(source)
        if len({source.source for source in sources}) != len(sources):
            return ()
        return tuple(sources)

    def reconcile(self, sessions):
        desired = {
            session['session_id']: session
            for session in sessions if session.get('active') is True
        }
        if self.job is not None:
            session_id = self.job.session['session_id']
            if session_id not in desired:
                self.job.stop('session_ended')
            if self.job.is_alive():
                return
            self.job.join()
            if self.job.session.get('stop_reason') == 'session_ended':
                self.finished.add(session_id)
            else:
                self.retry_after[session_id] = time.monotonic() + 30
            self.job = None
        for session_id, session in sorted(desired.items()):
            if session_id in self.finished or time.monotonic() < self.retry_after.get(session_id, 0):
                continue
            sources = self.sources_for(session)
            if not sources:
                print(f'Session {session_id}: recorder waiting for assigned camera IPs to match local sources.', flush=True)
                self.retry_after[session_id] = time.monotonic() + 30
                continue
            self.job = self.job_factory(session, sources, self.args, self.av)
            self.job.start()
            break

    def shutdown(self, reason='shutdown'):
        if self.job is not None:
            self.job.stop(reason)
            self.job.join()
            self.job = None

    def wait_for_sessions(self, stop_file=None):
        print('Recorder in standby, waiting for a started session.', flush=True)
        try:
            while stop_file is None or not stop_file.exists():
                try:
                    response = self.client.work()
                    self.reconcile(response.get('sessions', []))
                except (BackendRequestError, TimeoutError):
                    self.shutdown('backend_unavailable')
                    print('Recorder waiting for backend connection.', flush=True)
                for _tick in range(8):
                    if stop_file is not None and stop_file.exists():
                        break
                    time.sleep(0.25)
        finally:
            self.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Wait for started TAGAD sessions and record their assigned cameras.')
    parser.add_argument('--config', type=Path, default=REPO_ROOT / 'pipeline' / 'camera_sources.local.json')
    parser.add_argument('--output-root', type=Path, default=Path('C:/TAGAD_PRIVATE_PILOT'))
    parser.add_argument('--backend-url', default='http://127.0.0.1:8000')
    parser.add_argument('--stop-file', type=Path)
    options = parser.parse_args()
    api_key = os.environ.get('TAGAD_PIPELINE_API_KEY', '')
    if not api_key:
        print('Recorder requires the private pipeline API key.', file=sys.stderr)
        return 1
    try:
        args = SimpleNamespace(**vars(options), minutes=60)
        validate_inputs(args)
        import av
        av.logging.set_level(None)
        controller = RecordingController(
            BackendClient(options.backend_url, api_key, timeout=3, retries=0),
            load_configuration(options.config), args, av,
        )
        controller.wait_for_sessions(options.stop_file)
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        print(f'Recorder standby failed ({type(error).__name__}).', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
