<script setup>
import { computed } from 'vue';
import { useStudyStore } from '@/stores/study';

const store = useStudyStore();

const subjectsList = computed(() => {
  return Object.keys(store.subjects).map(folder => ({
    name: folder,
    displayName: formatSubjectName(folder),
    topicCount: store.subjects[folder].length,
    questionCount: store.questions.filter(q => q.source?.startsWith(folder + '/')).length
  }));
});

const formatSubjectName = (str) => {
  const overrides = {
    'medical_exam': 'Läkarexamen',
    'korkortsteori': 'Körkortsteori'
  };
  return overrides[str] || str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const selectSubject = (subjectName) => {
  store.selectSubject(subjectName);
};
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-4">
    <div class="max-w-2xl w-full space-y-8">
      <!-- Header -->
      <div class="text-center space-y-2">
        <h1 class="text-5xl font-extrabold text-stone-900">Iller6</h1>
        <p class="text-lg text-stone-600">Välj studieinriktning</p>
      </div>

      <!-- Subject Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          v-for="subject in subjectsList"
          :key="subject.name"
          @click="selectSubject(subject.name)"
          class="group relative overflow-hidden rounded-2xl border-2 border-stone-200 bg-white hover:border-indigo-400 hover:shadow-lg transition-all duration-200 p-6 text-left"
        >
          <div class="relative z-10">
            <h2 class="text-2xl font-bold text-stone-900 mb-2">
              {{ subject.displayName }}
            </h2>
            <div class="space-y-1 text-sm text-stone-600">
              <div>{{ subject.topicCount }} kategorier</div>
              <div>{{ subject.questionCount }} frågor</div>
            </div>
          </div>
          
          <!-- Hover effect -->
          <div class="absolute inset-0 bg-gradient-to-br from-indigo-50 to-purple-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
        </button>
      </div>

      <!-- Empty state -->
      <div v-if="subjectsList.length === 0" class="text-center py-12 text-stone-500">
        <p class="text-lg">Inga ämnen hittades.</p>
        <p class="text-sm mt-2">Lägg till innehåll i /data mappen.</p>
      </div>
    </div>
  </div>
</template>
