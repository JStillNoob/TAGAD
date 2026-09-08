export async function request(url, options = {}) {
  try {
    return await fetch(url, options)
  } catch {
    throw new Error('The backend server is unavailable. Check your connection and try again.')
  }
}
