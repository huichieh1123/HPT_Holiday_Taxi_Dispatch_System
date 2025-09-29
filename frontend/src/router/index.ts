import { createRouter, createWebHistory } from 'vue-router'
import BookingView from '../views/BookingView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'bookings',
      component: BookingView
    },
    {
      path: '/update-location/:bookingRef/:vehicleId',
      name: 'location-update',
      // route level code-splitting
      // this generates a separate chunk (LocationUpdate.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/LocationUpdateView.vue')
    }
  ]
})

export default router
