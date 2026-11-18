import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import LoginView from '../views/LoginView.vue'
import CompetitionsView from '../views/CompetitionsView.vue'
import CompetitionLayoutView from '../views/CompetitionLayoutView.vue'
import CompetitionOverviewView from '../views/CompetitionOverviewView.vue'
import ApplicationsView from '../views/ApplicationsView.vue'
import WeighInView from '../views/WeighInView.vue'
import CategoriesView from '../views/CategoriesView.vue'
import BracketsView from '../views/BracketsView.vue'
import ProtocolView from '../views/ProtocolView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/competitions' },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/competitions', name: 'competitions', component: CompetitionsView },
    {
      path: '/competitions/:id',
      component: CompetitionLayoutView,
      children: [
        { path: '', name: 'competition-overview', component: CompetitionOverviewView },
        { path: 'applications', name: 'competition-applications', component: ApplicationsView },
        { path: 'weigh-in', name: 'competition-weigh-in', component: WeighInView },
        { path: 'categories', name: 'competition-categories', component: CategoriesView },
        { path: 'brackets', name: 'competition-brackets', component: BracketsView },
        { path: 'protocol', name: 'competition-protocol', component: ProtocolView },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) return '/competitions'
    return true
  }

  if (!auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }

  if (!auth.user) {
    try {
      await auth.loadUser()
    } catch {
      auth.logout()
      return { name: 'login', query: { next: to.fullPath } }
    }
  }

  return true
})

export default router
