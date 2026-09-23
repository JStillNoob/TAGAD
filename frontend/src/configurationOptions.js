import { apiRequest } from './api'
import { paginationQuery } from './pagination'

export function fetchConfigurationOptions(kind, parameters = {}) {
  return apiRequest(`/api/auth/configuration-options/${paginationQuery({ kind, ...parameters })}`)
}
