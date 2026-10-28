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
import OrganizationsView from '../views/OrganizationsView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import { fetchCurrentUser } from '../auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',           component: LoginView, meta: { public: true } },
    { path: '/register',   component: RegisterView, meta: { public: true } },
    { path: '/forgot-password', component: ForgotPasswordView, meta: { public: true } },
    { path: '/reset-password/:uid/:token', component: ResetPasswordView, meta: { public: true, allowAuthenticated: true } },
    { path: '/dashboard',  component: DashboardView },
    { path: '/session',    component: SessionView, meta: { roles: ['org_admin', 'teacher'] } },
    { path: '/analytics',  component: AnalyticsView, meta: { roles: ['org_admin', 'teacher'] } },
    { path: '/classes',    component: ClassesView, meta: { roles: ['org_admin', 'teacher'] } },
    { path: '/students',   redirect: '/classes' },
    { path: '/reports',    component: ReportsView, meta: { roles: ['org_admin', 'teacher'] } },
    { path: '/logs',       component: SystemLogsView, meta: { roles: ['org_admin', 'teacher'] } },
    { path: '/settings',   component: SettingsView },
    {
      path: '/users',
      component: UserManagementView,
      meta: { roles: ['system_admin', 'org_admin'] },
    },
    {
      path: '/organizations',
      component: OrganizationsView,
      meta: { roles: ['system_admin'] },
    },
    { path: '/:pathMatch(.*)*', component: NotFoundView, meta: { public: true, allowAuthenticated: true } },
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
    if (user && !to.meta.allowAuthenticated) return safeRedirect(to.query.redirect)
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
