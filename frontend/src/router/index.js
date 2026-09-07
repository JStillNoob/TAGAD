import { createRouter, createWebHistory } from 'vue-router'
import LoginView    from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import SessionView  from '../views/SessionView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import ClassesView from '../views/StudentsView.vue'
import ReportsView from '../views/ReportsView.vue'
import SystemLogsView from '../views/SystemLogsView.vue'
import SettingsView from '../views/SettingsView.vue'
import UserManagementView from '../views/UserManagementView.vue'
import { fetchCurrentUser } from '../auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',           component: LoginView, meta: { public: true } },
    { path: '/register',   component: RegisterView, meta: { public: true } },
    { path: '/dashboard',  component: DashboardView },
    { path: '/session',    component: SessionView },
    { path: '/analytics',  component: AnalyticsView },
    { path: '/classes',    component: ClassesView },
    { path: '/students',   redirect: '/classes' },
    { path: '/reports',    component: ReportsView },
    { path: '/logs',       component: SystemLogsView },
    { path: '/settings',   component: SettingsView },
    {
      path: '/users',
      component: UserManagementView,
      meta: { roles: ['system_admin', 'org_admin'] },
    },
  ],
})

function safeRedirect(value) {
  return typeof value === 'string'
    && value.startsWith('/')
    && !value.startsWith('//')
    ? value
    : '/dashboard'
}

router.beforeEach(async (to) => {
  let user
  try {
    user = await fetchCurrentUser()
  } catch {
    if (to.meta.public) return true
    return { path: '/', query: { redirect: to.fullPath } }
  }

  if (to.meta.public) {
    if (user) return safeRedirect(to.query.redirect)
    return true
  }

  if (!user) {
    return { path: '/', query: { redirect: to.fullPath } }
  }

  if (to.meta.roles && !to.meta.roles.includes(user.role)) {
    return { path: '/dashboard' }
  }

  return true
})
