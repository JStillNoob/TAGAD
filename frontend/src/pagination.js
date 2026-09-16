export function paginationQuery(parameters = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(parameters)) {
    if (value !== '' && value !== null && value !== undefined) query.set(key, value)
  }
  const rendered = query.toString()
  return rendered ? `?${rendered}` : ''
}
