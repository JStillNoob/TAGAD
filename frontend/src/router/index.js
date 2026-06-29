import { createRouter, createWebHistory } from 'vue-router'
import LoginView    from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import SessionView  from '../views/SessionView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import StudentsView from '../views/StudentsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',           component: LoginView },
    { path: '/dashboard',  component: DashboardView },
    { path: '/session',    component: SessionView },
    { path: '/analytics',  component: AnalyticsView },
    { path: '/students',   component: StudentsView },
  ],
})
