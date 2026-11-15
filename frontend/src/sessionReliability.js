export function findOwnActiveSession(sessions, userId) {
  return sessions.find((session) => (
    session.user === userId && session.status === 'ongoing'
  )) || null
}

export function findOwnPreparedSession(sessions, userId) {
  return sessions.find((session) => (
    session.user === userId && session.status === 'preparing'
  )) || null
}

export function restoreSlideIndex(session) {
  const slides = session?.presentation?.slides || []
  const savedIndex = slides.findIndex((slide) => slide.id === session?.current_slide)
  return savedIndex >= 0 ? savedIndex : 0
}

export async function startSessionWithRecovery({ start, fetchSessions, userId, sessionId, fetchSession }) {
  try {
    return await start()
  } catch (originalError) {
    try {
      const recovered = fetchSession
        ? await fetchSession(sessionId)
        : findOwnActiveSession(await fetchSessions(), userId)
      if (recovered?.user === userId && (!sessionId || recovered.id === sessionId)) {
        if (recovered.status === 'ongoing' || recovered.ended_at) return recovered
        originalError.recoveredSession = recovered
      }
    } catch (readError) {
      originalError.recoveryPending = readError.status !== 404
    }
    throw originalError
  }
}

export async function endSessionWithRecovery({ sessionId, end, fetchSessions, fetchSession, action = 'finish' }) {
  try {
    return await end()
  } catch (originalError) {
    try {
      const recovered = fetchSession
        ? await fetchSession(sessionId)
        : (await fetchSessions()).find(session => session.id === sessionId)
      originalError.recoveredSession = recovered
      if (recovered?.id === sessionId && (recovered.status === 'completed' || recovered.ended_at)) {
        if ((recovered.end_action || 'finish') === action) return recovered
        originalError.message = 'This class closed with a different action. Its current state is displayed.'
      }
    } catch (readError) {
      originalError.recoveryPending = readError.status !== 404
    }
    throw originalError
  }
}

export async function continueLessonWithRecovery({ prepare, lessonId, requestId, fetchLesson, fetchSession }) {
  try {
    return await prepare()
  } catch (originalError) {
    try {
      const lesson = await fetchLesson(lessonId)
      originalError.recoveredLesson = lesson
      const sessionId = lesson.prepared_session || lesson.active_session || lesson.latest_session
      if (sessionId) {
        const session = await fetchSession(sessionId)
        if (session.lesson?.id === lessonId) {
          originalError.recoveredSession = session
          if (session.continuation_request_id === requestId) return session
        }
      }
    } catch (readError) {
      originalError.recoveryPending = readError.status !== 404
    }
    throw originalError
  }
}

export async function finishLessonWithRecovery({ finish, lessonId, fetchLesson }) {
  try {
    return await finish()
  } catch (originalError) {
    try {
      const lesson = await fetchLesson(lessonId)
      originalError.recoveredLesson = lesson
      if (lesson.state === 'completed') return lesson
    } catch (readError) {
      originalError.recoveryPending = readError.status !== 404
    }
    throw originalError
  }
}
