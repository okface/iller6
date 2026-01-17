<script setup>
import { onMounted } from 'vue';
import { useStudyStore } from '@/stores/study';
import Dashboard from '@/components/Dashboard.vue';
import Quiz from '@/components/Quiz.vue';

const store = useStudyStore();

onMounted(() => {
  store.loadContent();
});
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-stone-100 via-amber-50/40 to-rose-100/40 text-slate-900 font-sans">
    <div v-if="store.loading" class="flex items-center justify-center h-screen">
      <div class="text-xl animate-pulse text-indigo-600 font-bold">Loading Iller5...</div>
    </div>
    
    <div v-else-if="store.error" class="flex items-center justify-center h-screen">
      <div class="text-red-600 bg-red-100 p-8 rounded-lg shadow-lg max-w-md">
        <h2 class="font-bold text-lg mb-2">Error</h2>
        {{ store.error }}
        <button @click="location.reload()" class="mt-4 text-sm underline display-block">Reload</button>
      </div>
    </div>

    <div v-else class="max-w-2xl mx-auto min-h-screen bg-stone-50 md:bg-stone-50/90 shadow-xl border-x border-stone-200 flex flex-col relative">
      <!-- Main Content Area -->
      <main class="flex-grow p-4 md:p-6">
        <transition name="fade" mode="out-in">
          <Dashboard v-if="store.view === 'dashboard'" />
          <Quiz v-else-if="store.view === 'quiz'" />
        </transition>
      </main>
    </div>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
