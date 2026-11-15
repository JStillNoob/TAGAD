import assert from 'node:assert/strict'
import test from 'node:test'
import { lessonState, meetingOutcome } from '../src/sessionLabels.js'

test('closed meetings keep their outcome when the linked lesson is later completed', () => {
  const meeting = { end_action: 'save', lesson: { state: 'completed' } }
  assert.equal(meetingOutcome(meeting), 'Class saved')
  assert.equal(lessonState(meeting), 'Completed')
  assert.equal(meetingOutcome({ end_action: 'finish' }), 'Class finished')
  assert.equal(lessonState({ lesson_state: 'saved' }), 'Saved for Later')
})

test('legacy meetings retain completion wording and no lesson label', () => {
  assert.equal(meetingOutcome({ status: 'completed' }), 'Completed')
  assert.equal(meetingOutcome({ status: 'ongoing' }), 'In progress')
  assert.equal(meetingOutcome({ status: 'preparing' }), 'Preparing')
  assert.equal(lessonState({}), '')
})
