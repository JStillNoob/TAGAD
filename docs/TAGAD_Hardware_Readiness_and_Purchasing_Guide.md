# TAGAD Hardware Readiness and Purchasing Guide

Last reviewed: September 28, 2026

## Decision

**Current status:** The CUDA and 60-minute simulated stability gates passed on
September 24, 2026. The remaining purchasing gate is one physical-camera RTSP
and classroom-placement pilot.

The proposed setup is suitable for TAGAD as a capstone system, but purchasing
all three cameras should wait until the remaining physical-camera acceptance
gate passes:

1. ~~CUDA must work in the TAGAD pipeline environment.~~ Passed September 24, 2026.
2. One physical camera must pass a real-classroom placement and RTSP pilot.

Hardware can provide stable, high-quality video, but it cannot by itself fix
poor camera angles or model-classification accuracy.

## Verified processing computer

The current processing computer was checked locally:

| Component | Verified value |
| --- | --- |
| Laptop | MSI Thin 15 B12VE |
| CPU | Intel Core i5-12450H, 8 cores / 12 logical processors |
| Memory | 24 GB DDR4-3200: one 8 GB module and one 16 GB module |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB GDDR6 |
| GPU power class | Up to 45 W maximum graphics power |
| System storage | 512 GB Micron NVMe SSD |
| Secondary storage | 1 TB Samsung 870 EVO SATA SSD |

This laptop is suitable for development and the initial classroom pilot. The
45 W laptop RTX 4050 is not equivalent to a desktop RTX 4050-class processor,
so sustained performance must be measured rather than assumed.

Official reference: [MSI Thin 15 B12VE specifications](https://www.msi.com/Laptop/Thin-15-B12VX/Specification)

## Verified CUDA acceleration

The project-local `pipeline\.venv` currently reports:

```text
PyTorch: 2.14.0+cu126
CUDA available: True
CUDA runtime: 12.6
GPU: NVIDIA GeForce RTX 4050 Laptop GPU
```

Verification command:

```powershell
pipeline\.venv\Scripts\python.exe -c "import torch; print('Torch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('Runtime:', torch.version.cuda); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU ONLY')"
```

The 60-minute three-source CUDA stability run completed 37,779 analyses at
3.498 analyses/second per source. Process memory peaked at 1,667 MB and ended
at 775 MB, GPU memory stayed around 422–656 MiB, and observed GPU temperature
was 47–52°C. This passes the simulated stability gate. MediaPipe, tracking,
decoding, and the SVM classifiers still use CPU resources, and short repeated
clips do not validate classroom accuracy. See
[`PIPELINE_BENCHMARK_REPORT.md`](PIPELINE_BENCHMARK_REPORT.md) for the full
record.

## Recommended hardware

| Component | Recommended specification | Quantity | Decision |
| --- | --- | ---: | --- |
| IP camera | 4 MP, fixed turret, PoE, RTSP, ONVIF, H.264, adjustable exposure/WDR | Pilot with 1, eventually 3 | Conditionally approved |
| Lens | 2.8 mm Front pilot; consider 4 mm for Left/Right after measuring coverage | Per camera | Must be tested |
| PoE switch | At least four Gigabit PoE ports, 802.3af/at, at least 56 W total budget | 1 | Approved |
| Ethernet | Pure-copper Cat6, not copper-clad aluminium | 3 camera runs plus uplinks | Approved |
| Mounts | Rigid, adjustable wall or ceiling mounts | 3 | Approved after placement plan |
| UPS | Approximately 650–1000 VA with adequate watt rating and runtime | 1 | Approved after load calculation |
| Processing computer | Existing MSI Thin 15, connected to AC power | 1 | Approved for pilot |
| NVR | Not required for normal TAGAD processing | 0 | Defer unless the school requires recording |

## Candidate camera: TP-Link VIGI C440I

The VIGI C440I is technically compatible with TAGAD. Official specifications
include:

- 4 MP maximum resolution
- 2.8 mm and 4 mm lens variants
- PoE using IEEE 802.3af/at
- RTSP streaming
- ONVIF compatibility
- H.264 and H.265 encoding
- Main-stream resolutions including 1080p and 4 MP
- Frame rates up to 30 FPS

Official reference: [VIGI C440I specifications](https://www.vigi.com/br/business-networking/vigi-network-camera/vigi-c440i/v1/)

Important limitations:

- Its low-resolution substream is only up to approximately 640×480 and will
  probably make distant faces too small.
- Start with the 1080p main stream, not the low-resolution substream.
- Start with H.264 for simpler OpenCV compatibility and troubleshooting.
- Confirm that the exact regional unit sold by the supplier has the requested
  lens; listings may carry only one lens version.
- Strong backlighting from classroom windows may require better true-WDR
  performance than this model provides.
- It is primarily an indoor camera, which is appropriate for a classroom.

## Lens and placement decision

Do not assume that all three cameras should use the same 4 mm lens.

| Lens | Approximate horizontal field of view | Tradeoff |
| --- | ---: | --- |
| 2.8 mm | 88.8 degrees | Covers more room, but faces appear smaller |
| 4 mm | 75.1 degrees | Larger faces, but less room coverage |

A published study describes UM Matina classrooms as typically seven metres by
nine metres. It surveyed lecture rooms across the campus and does not establish
that every Senior High School room has those exact dimensions, so `7 m × 9 m`
is only a provisional planning assumption. At a four-metre subject distance,
the 2.8 mm lens covers approximately 7.8 metres horizontally, while the 4 mm
lens covers approximately 6.1 metres. This makes 2.8 mm the safer first choice
when the Front camera must cover a roughly seven-metre-wide classroom.

Reference: [Reverberation Time of University of Mindanao Matina Campus
Classrooms](https://journals.upd.edu.ph/index.php/muhon/article/download/8891/7815/)

Provisional arrangement before the physical-room survey:

| Position | Provisional lens | Reason |
| --- | --- | --- |
| Front/Center | 2.8 mm | Prioritize complete classroom-width coverage for official analytics |
| Left | 4 mm only if measured coverage is sufficient | Gain facial detail across the room |
| Right | 4 mm only if measured coverage is sufficient | Gain facial detail across the room |

Mixing 2.8 mm and 4 mm C440I variants is supported because each camera is an
independent RTSP source. Keep resolution, codec, frame rate, and exposure as
consistent as practical. The Front source remains the official analytics
source until cross-camera duplicate handling is validated.

Before choosing the final lens, record:

- Classroom width and length
- Mounting height
- Distance to the nearest and farthest occupied seats
- Width of the widest student row
- Window and lighting positions
- Expected Front, Left, and Right fields of view
- Occlusions caused by other students, furniture, and the teacher

The existing short-video benchmark found approximately 77.5% valid-face
coverage for Center, 40.6% for Left, and 41% for Right. Camera placement must
improve the side views; purchasing more pixels alone may not solve oblique or
obstructed faces.

## Initial stream settings

Use these as the first pilot settings, then adjust from measured results:

```text
Camera output:       1920×1080 main stream
Codec:              H.264
Stream frame rate:  15 FPS
TAGAD analysis rate: 2.5 analyses/second per camera initially
Bitrate:            Use the camera's normal quality setting; avoid extreme compression
Audio:              Disabled or ignored
Continuous storage: Disabled unless explicitly required
```

The verified 60-minute CUDA three-source run sustained:

```text
Front: 3.498 analyses/second
Left:  3.498 analyses/second
Right: 3.498 analyses/second
```

Keep the initial live pilot at 2.5 analyses/second per camera. The CUDA test
shows headroom, but physical RTSP decoding and a continuous classroom scene
still need measurement before increasing the rate.

## PoE switch: four powered ports are enough

TAGAD needs three powered camera ports and one ordinary uplink port. An
eight-port PoE switch is not required for the planned three-camera pilot.

The compact TP-Link TL-SG1005P is the recommended pilot size. Current hardware
revisions provide:

- Five Gigabit Ethernet ports total
- Four PoE/PoE+ camera ports and one non-PoE uplink
- Up to 30 W per PoE+ port on current revisions
- A 65 W total PoE budget on current revisions; some older regional revisions
  are 802.3af with a 56 W budget
- Fanless operation

Official references: [current TL-SG1005P datasheet](https://static.tp-link.com/upload/product-overview/2026/202606/20260612/TL-SG1005P%28UN%296.0_datasheet.pdf)
and [product specifications](https://www.tp-link.com/us/business-networking/soho-switch-poe/tl-sg1005p/v1/).

Both the 56 W and 65 W versions have ample budget for three C440I cameras. The
C440I specification lists 5 W maximum on 12 V DC and 802.3af/at PoE class 0;
even the class-0 allocation for three units remains below 56 W. Confirm the
exact switch revision, included power adapter, four powered ports, and 802.3af
compatibility with the seller. Choose an eight-port model only if the school
expects a fourth camera, access points, phones, or near-term room expansion.

## Network and privacy setup

- Prefer wired Ethernet for every camera.
- Give cameras DHCP reservations or documented static addresses.
- Place cameras on an isolated VLAN or private camera network when possible.
- Prevent direct internet access from cameras unless explicitly required.
- Change every factory password before testing.
- Store RTSP usernames, passwords, and URLs only in the ignored local pipeline
  configuration or another approved secret store.
- Never commit RTSP URLs or credentials to Git.
- Never display camera credentials in the frontend or API responses.
- Do not store frames, face crops, landmarks, or temporary track identities.
- Decide whether the institution requires consent notices or a formal data
  retention policy before the classroom pilot.

Three camera streams at a few megabits per second each are easily within a
Gigabit network's capacity. Stable wiring, addressing, and access control are
more important than raw bandwidth.

## Power and thermal requirements

- Keep the laptop connected to its original 120 W AC adapter during inference.
- Use the laptop's performance mode during benchmarks and classroom sessions.
- Ensure that cooling vents are unobstructed.
- Record CPU temperature, GPU temperature, clock rate, memory use, and analysis
  throughput during a 60–90 minute test.
- Put the PoE switch and router on the UPS.
- If the laptop adapter is also connected to the UPS, confirm that the UPS watt
  rating supports the adapter, switch, router, and cameras simultaneously.
- Choose the UPS based on required runtime, not VA alone.

## Purchasing sequence

Do not purchase everything at once. Use this order:

1. [x] Install and verify CUDA-enabled PyTorch in the dedicated pipeline environment.
2. [x] Rerun the pipeline unit tests.
3. [x] Rerun the three-video concurrent benchmark with CUDA.
4. [x] Record GPU memory, CPU, RAM, temperatures, and per-camera throughput.
5. [ ] Measure the intended classroom and draw the three coverage zones.
6. [ ] Borrow or purchase one 2.8 mm VIGI C440I Front pilot camera.
7. [ ] Use a PoE injector or the intended PoE switch for the pilot.
8. [ ] Confirm the camera opens through RTSP using OpenCV.
9. [ ] Confirm H.264 1080p at 15 FPS remains stable for 60–90 minutes.
10. [ ] Capture a representative lesson with proper approval.
11. [ ] Measure valid-face and classification coverage at near and far seats.
12. [ ] Check bright-window, ordinary-light, and low-light conditions.
13. [ ] Confirm the laptop does not thermally throttle.
14. [ ] Confirm session start, slide changes, camera recovery, and session end.
15. [ ] Select the remaining lens variants from measured room coverage.
16. [ ] Purchase the remaining two cameras and permanent mounting equipment.

## Pilot acceptance gate

Do not approve the final three-camera purchase until all items pass:

- [x] `torch.cuda.is_available()` returns `True`.
- [x] The benchmark confirms that YOLO is using the RTX 4050.
- [ ] One physical RTSP stream runs continuously for at least 60–90 minutes.
- [ ] The farthest occupied seats produce usable head and facial landmarks.
- [ ] Bright windows do not make students unusably dark.
- [ ] The selected lens covers the required seats without excessive empty area.
- [ ] Processing throughput remains above the agreed analysis-rate target.
- [ ] CPU, GPU, and memory use remain stable after warm-up.
- [ ] The laptop does not sustain thermal throttling.
- [ ] Disconnecting the camera shows Reconnecting or Offline without ending the session.
- [ ] Reconnecting the camera restores Online state without duplicate official summaries.
- [ ] No image, face crop, local path, RTSP URL, or credential appears in logs.
- [ ] Teachers can start and end the session without controlling worker terminals.

## Final conclusion

The recommended wired PoE architecture is appropriate. The existing laptop
passed the simulated CUDA stability gate, and the proposed C440I camera and a
four-port PoE switch are compatible with TAGAD. Use a 2.8 mm Front camera for
the initial coverage pilot; 4 mm Left/Right variants remain an option after the
actual room is measured. Approval of the final three-camera purchase remains
conditional on a successful one-camera RTSP and classroom-placement test.
Camera placement and model validation will affect system quality more than
purchasing three cameras immediately.
