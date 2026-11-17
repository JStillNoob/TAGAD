<script setup>
import ThemeToggle from './ThemeToggle.vue'

defineProps({
  accent: { type: String, required: true },
  description: { type: String, required: true },
  wide: { type: Boolean, default: false },
})
</script>

<template>
  <div class="login-page auth-shell">
    <ThemeToggle class="login-theme-toggle" />
    <div class="login-frame">
      <section class="login-brand-panel" aria-labelledby="auth-brand-title">
        <div class="login-brand-content">
          <img src="/illustrations/login-classroom.png" width="1536" height="1024" alt="" aria-hidden="true" class="login-illustration">
          <h1 id="auth-brand-title" class="login-brand-title">TAGAD</h1>
          <p class="login-brand-accent">{{ accent }}</p>
          <p class="login-brand-copy">{{ description }}</p>
          <div class="login-brand-dots" aria-hidden="true"><span></span><span></span><span></span></div>
        </div>
      </section>

      <main class="auth-content login-content">
        <div class="login-card-wrap" :class="{ 'auth-shell-wide': wide }">
          <div class="login-logo-lockup"><img src="/tagad_logo.svg" width="44" height="44" alt=""><span>TAGAD</span></div>
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
