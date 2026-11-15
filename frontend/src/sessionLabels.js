export function meetingOutcome(session) {
  if (session.end_action === 'save') return 'Class saved'
  if (session.end_action === 'finish') return 'Class finished'
  if (session.status === 'preparing') return 'Preparing'
  return session.ended_at || session.status === 'completed' ? 'Completed' : 'In progress'
}

export function lessonState(session) {
  const state = session.lesson?.state || session.lesson_state
  return { saved: 'Saved for Later', active: 'Active', completed: 'Completed' }[state] || ''
}
