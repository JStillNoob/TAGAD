<script setup>
import AppLayout from '../layouts/AppLayout.vue'

const organization = {
  organization_name: 'Bulacan State University',
  organization_code: 'BULSU-MAIN',
  address: 'City of Malolos, Bulacan, Philippines',
  contact_email: 'info@bulsu.edu.ph',
  contact_no: '(044) 791-0153',
  status: 'Active',
  created_at: 'Jan 12, 2026',
}

const user = {
  username: 'dsantos',
  first_name: 'Maria',
  middle_name: 'Reyes',
  last_name: 'Santos',
  email: 'dr.santos@bulsu.edu.ph',
  contact_no: '0917-123-4567',
  role: 'Teacher',
  status: 'Active',
}

const orgFields = [
  { label: 'Organization Name', value: organization.organization_name },
  { label: 'Organization Code', value: organization.organization_code },
  { label: 'Address', value: organization.address },
  { label: 'Contact Email', value: organization.contact_email },
  { label: 'Contact No.', value: organization.contact_no },
  { label: 'Date Registered', value: organization.created_at },
]

const userFields = [
  { label: 'Username', value: user.username },
  { label: 'First Name', value: user.first_name },
  { label: 'Middle Name', value: user.middle_name },
  { label: 'Last Name', value: user.last_name },
  { label: 'Email', value: user.email },
  { label: 'Contact No.', value: user.contact_no },
  { label: 'Role', value: user.role },
]
</script>

<template>
  <AppLayout page-title="Settings">

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- Organization profile -->
      <div class="page-card p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-semibold text-navy">Organization Profile</h3>
          <span class="badge-engaged">{{ organization.status }}</span>
        </div>
        <div class="divide-y divide-gray-50">
          <div v-for="f in orgFields" :key="f.label" class="flex items-center justify-between py-3">
            <span class="text-xs text-gray-400">{{ f.label }}</span>
            <span class="text-sm font-medium text-navy text-right">{{ f.value }}</span>
          </div>
        </div>
      </div>

      <!-- User profile -->
      <div class="page-card p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-semibold text-navy">User Profile</h3>
          <span class="badge-engaged">{{ user.status }}</span>
        </div>
        <div class="flex items-center gap-3 mb-5">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0" style="background:#465FF1;">MS</div>
          <div>
            <p class="text-sm font-semibold text-navy">{{ user.first_name }} {{ user.last_name }}</p>
            <p class="text-xs text-gray-400">{{ user.role }} · {{ organization.organization_name }}</p>
          </div>
        </div>
        <div class="divide-y divide-gray-50">
          <div v-for="f in userFields" :key="f.label" class="flex items-center justify-between py-3">
            <span class="text-xs text-gray-400">{{ f.label }}</span>
            <span class="text-sm font-medium text-navy text-right">{{ f.value }}</span>
          </div>
        </div>
      </div>

    </div>
  </AppLayout>
</template>
