# TAGAD Classroom Ground-Truth Protocol

Last updated: November 5, 2026  
Status: Protocol ready; institutional approval and classroom collection pending

## Purpose

This protocol defines how the TAGAD team will collect and review a small,
consented classroom dataset for model validation. It creates evidence for
measuring classification quality without adding attendance, face recognition,
student profiles, or persistent identity tracking to TAGAD.

This document is a project procedure, not legal advice or institutional
approval. The school, research adviser, ethics body, and privacy officer decide
which approvals and consent or assent forms are required before collection.

## Hard permission gate

Do not start a recording until every applicable item below is documented:

- [ ] Written school or institution authorization.
- [ ] Research adviser or ethics-review approval or written determination.
- [ ] Teacher authorization for the scheduled classroom activity.
- [ ] A clear participant information notice describing purpose, cameras,
      processing, access, retention, withdrawal, and contact details.
- [ ] Freely given, specific, informed participant consent where required.
- [ ] Parent or guardian consent and student assent for minors where required
      by the institution and applicable rules.
- [ ] A non-coercive option for anyone who will not participate, with no effect
      on grades, standing, or access to instruction.
- [ ] Approval of the exact private storage location and deletion date.
- [ ] Named authorized roles for capture, custody, and review.

Consent forms and participant names must be held by the authorized institution
or designated data custodian. They must not be placed in the TAGAD repository,
the annotation dataset, filenames, model outputs, reports, or chat messages.

## Privacy principles

- Collect only the footage and metadata needed for the declared validation.
- Use the footage only for the approved TAGAD research purpose.
- Never use face recognition or attempt to identify a student.
- Do not store names, student numbers, attendance lists, biometric templates,
  or persistent cross-session tracking identifiers.
- Do not use pilot results to make decisions about an individual student.
- Restrict raw-media access to authorized project roles.
- Keep raw video, review exports, and derived sensitive data off Git, personal
  messaging applications, public cloud links, and shared screenshots.
- Report only aggregate results and de-identified examples approved for use.

These controls implement data minimization, declared purpose, confidentiality,
limited retention, and appropriate safeguards. They do not replace review by
the institution's authorized privacy and research personnel.

## Private storage layout

Use an encrypted, access-controlled folder outside the repository. A local
example is:

```text
C:\TAGAD_PRIVATE_PILOT\PILOT-YYYYMMDD-01\
    approvals\
    raw\
        front\
        left\
        right\
    review\
        reviewer-r1\
        reviewer-r2\
    agreed\
    deletion-record\
```

The session code contains a date and sequence only. Filenames must not contain
a school name, classroom name, teacher name, student name, student number, or
other participant identifier.

If private pilot material is temporarily placed inside the workspace despite
this rule, it must be under an ignored directory named `private_pilot_data`,
`pilot_media`, or `ground_truth_private`. Outside-repository storage remains
the preferred and safer location.

## Session metadata sheet

Create one private metadata sheet per approved recording. Record only:

Start from the blank
[`A3_PILOT_RECORD_TEMPLATE.md`](A3_PILOT_RECORD_TEMPLATE.md), copied to the
encrypted private session folder. Never fill the tracked repository copy.

| Field | Rule |
| --- | --- |
| Session code | Date plus sequence; no school or participant name. |
| Approval reference | Institution-issued reference or `confirmed`; no consent-form copy. |
| Capture date and time | Local date/time with `Asia/Singapore` timezone. |
| Activity context | Lecture, reading, note-taking, individual task, group work, recitation, or transition. |
| Enrolled class size | Aggregate number supplied by the institution. |
| Students present | Anonymous aggregate headcount; never a list of names. |
| Participating/recordable count | Anonymous aggregate covered by the approved procedure. |
| Camera codes | Front, Left, and Right plus non-secret device identifier. |
| Camera clock offsets | Measured difference from the processing computer. |
| Capture start/end | Timestamp for each camera file. |
| Retention deadline | Concrete deletion date, no later than 30 days after capture. |
| Authorized roles | Role names such as custodian, operator, R1, and R2; keep personal names separately. |
| Incidents or exclusions | Counts and non-identifying notes only. |

The anonymous present count exists only to distinguish enrollment, physical
attendance, consent coverage, camera visibility, and model detections. It is
not a TAGAD attendance feature.

## Clock and three-camera synchronization

Before students enter or before approved recording begins:

1. Set the processing computer and all cameras to the same timezone and NTP
   source where supported.
2. Compare each camera overlay time with the processing computer and record
   the offset in milliseconds or seconds.
3. Start Front, Left, and Right capture for the same session code.
4. Create one neutral synchronization cue visible to all three cameras, such as
   an approved board flash or raised marker, without naming a participant.
5. Record the cue time in the metadata sheet.
6. Repeat the cue at the end when practical to detect clock drift.
7. Do not compare camera observations until offsets have been corrected.

## Collection procedure

The automatic session recorder and storage behavior are documented under
[Record the approved beta test](../pipeline/README.md#record-the-approved-beta-test).
With approved recording enabled locally, the usual TAGAD startup launches the
recorder in standby. It captures selected cameras while the session is active.
Retain its manifest with the private pilot record.

1. Confirm the hard permission gate and private storage location.
2. Record enrollment and students-present values as anonymous counts.
3. Verify camera framing and exclude teacher-only or irrelevant areas where
   practical; camera geometry calibration itself belongs to A4.
4. Record the synchronization cue and the planned lesson activity context.
5. Capture the approved Front, Left, and Right streams for the minimum duration
   needed for validation.
6. Do not ask students to imitate emotions or behavior unless a separate,
   specifically approved staged-calibration procedure exists.
7. Stop capture immediately if the approved scope, consent conditions, or
   privacy safeguards cannot be maintained.
8. Move files directly to private storage and verify that none appear in Git.

Target naturally occurring examples where available: active participation,
quiet listening, note-taking, reading, visible uncertainty, lesson-related
group discussion, low-activation/resting patterns, looking away, and clearly
unrelated device use. Absence of a rare state must be reported honestly rather
than filled with an invented label.

## Five-second annotation windows

Follow [`ENGAGEMENT_LABEL_GUIDE.md`](ENGAGEMENT_LABEL_GUIDE.md). Reviewers label
complete five-second windows, not isolated frames.

Each private annotation row contains:

R1 and R2 each use a separate private copy of
[`A3_REVIEWER_WORKSHEET_TEMPLATE.md`](A3_REVIEWER_WORKSHEET_TEMPLATE.md).

| Field | Allowed content |
| --- | --- |
| Session code | Anonymous session code. |
| Camera | Front, Left, or Right. |
| Window start/end | Corrected timestamps. |
| Sample reference | Random or window-local code; never reused as identity. |
| Activity context | One approved context value. |
| Visibility | Sufficient, partial, or insufficient. |
| Label | Engaged, Attentive, Confused, Bored, Disengaged, or Uncertain. |
| Reviewer | R1 or R2 code. |
| Note | Short observable reason; no identity or personal judgment. |

Use `Uncertain` when the evidence is weak, conflicting, occluded, or dependent
on unknown lesson context. It maps to TAGAD's `Unclassified` result. A sample
reference locates an observation for private comparison only; it must not be
used to identify or track a participant across sessions.

## Independent review and agreement

1. R1 and R2 receive the same approved windows and the label guide.
2. They annotate independently without seeing each other's labels.
3. Compare labels only after both copies are complete.
4. Record exact agreements, disagreements, and per-state counts.
5. Discuss each disagreement using observable evidence and activity context.
6. Keep a supported agreed label only when both reviewers can justify it.
7. Otherwise retain `Uncertain`/`Unclassified`; never force agreement.
8. Record the final aggregate agreement rate and limitations. Do not call it
   model accuracy.

Only the agreed annotations may be used as ground truth for later model
evaluation. Pipeline predictions must not be shown to reviewers before they
finish independent annotation.

## Balance and dataset separation

- Maintain a private count ledger by label, activity context, and camera.
- Do not duplicate adjacent frames from one behavior to manufacture balance.
- If a state is scarce, collect another approved session or report the gap.
- Keep complete classroom sessions together in one split. Do not divide nearby
  windows from the same session between training, validation, and test sets.
- Select the test sessions before tuning thresholds or retraining models.
- Do not use the final test sessions to choose features, thresholds, or models.
- Report the number of sessions, windows, cameras, and Unclassified samples in
  every split.

Session-level separation is the default because TAGAD does not identify
participants. This prevents near-duplicate windows from the same recording
appearing on both sides of an evaluation.

## Retention and deletion

| Material | Retention rule |
| --- | --- |
| Consent/assent and approval records | Held separately by the authorized institution under its approved schedule; never in the TAGAD dataset or repository. |
| Raw classroom video/audio | Video only unless audio is explicitly approved. Delete immediately after annotation and quality review, and no later than 30 days after capture. |
| Temporary frames or crops | Do not create by default. If specifically approved and required, protect and delete them with the raw video. |
| Private reviewer files with observation references | Delete after agreement, paired evaluation, and audit are complete, within the approved project schedule. |
| De-identified agreed labels and aggregate metrics | Retain only through the approved capstone evaluation period, then archive or delete under institutional direction. |
| Model artifacts trained from approved data | Retain only if the approval covers derived artifacts and release; never publish without a separate review. |

Deletion means removing working copies, exports, temporary files, and reachable
backups under the team's control. Create a deletion record containing only the
session code, material category, deletion date, responsible role, and result.
If an approved retention schedule is shorter than this protocol, the shorter
schedule wins. Any longer period requires written institutional approval.

## Withdrawal, exclusion, and incidents

- Follow the approved consent and institutional procedure for withdrawal or
  exclusion; do not improvise a new legal basis.
- Quarantine affected material immediately while the custodian determines the
  required deletion or restriction.
- Do not post a privacy incident, participant information, or raw frame in an
  issue tracker or chat. Contact the authorized adviser/privacy officer.
- Document only a non-identifying incident reference in the project log.

## A3 completion evidence

A3 is complete only when the project can show all of the following without
exposing participants:

- Approved permission references and declared retention date.
- Anonymous enrollment, present, and recordable counts.
- Corrected Front, Left, and Right timing plus synchronization evidence.
- Consented timestamped windows covering the observable behaviors available.
- Independent R1 and R2 annotations and a recorded resolution outcome.
- A label-balance ledger including Uncertain/Unclassified.
- Session-separated training, validation, and test manifests.
- Confirmation that raw and derived private material is absent from Git.
- A completed deletion record when the retention deadline is reached.

## Official privacy references

- Republic Act No. 10173, Data Privacy Act of 2012:
  <https://officialgazette.gov.ph/2012/15/republic-act-no-10173>
- National Privacy Commission Circular No. 2023-04, Guidelines on Consent:
  <https://privacy.gov.ph/wp-content/uploads/2023/11/NPC-Circular-No.-2023-04_Guidelines-on-Consent_07Nov2023.pdf>
- Implementing Rules and Regulations of Republic Act No. 10173:
  <https://privacy.gov.ph/implementing-rules-regulations-data-privacy-act-2012/>
