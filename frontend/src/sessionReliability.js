export function findOwnActiveSession(sessions, userId) {
  return sessions.find((session) => (
    session.user === userId && session.status === 'ongoing'
  )) || null
}

export function restoreSlideIndex(session) {
  const slides = session?.presentation?.slides || []
  const savedIndex = slides.findIndex((slide) => slide.id === session?.current_slide)
  return savedIndex >= 0 ? savedIndex : 0
}

export async function startSessionWithRecovery({ start, fetchSessions, userId }) {
  try {
    return await start()
  } catch (originalError) {
    try {
      const activeSession = findOwnActiveSession(await fetchSessions(), userId)
      if (activeSession) return activeSession
    } catch {
      // Preserve the original start failure when the recovery check also fails.
    }
    throw originalError
  }
}

export async function endSessionWithRecovery({ sessionId, end, fetchSessions }) {
  try {
    return await end()
  } catch (originalError) {
    try {
      const completedSession = (await fetchSessions()).find((session) => (
        session.id === sessionId
        && (session.status === 'completed' || Boolean(session.ended_at))
      ))
      if (completedSession) return completedSession
    } catch {
      // Preserve the original end failure when the recovery check also fails.
    }
    throw originalError
  }
}
