<script setup>
import { computed, ref } from 'vue';
import { useStudyStore } from '@/stores/study';

const store = useStudyStore();

const showCategoryPicker = ref(false);
const selectedSources = ref(new Set());

// Group subjects for display
// store.subjects is { folder: [file1, file2] }
const subjectsList = computed(() => {
  return Object.keys(store.subjects).map(folder => ({
    name: folder,
    topics: store.subjects[folder]
  }));
});

const totalQuestions = computed(() => store.questions?.length || 0);
const answeredCount = computed(() => {
  let n = 0;
  for (const q of store.questions || []) {
    const p = store.progress?.[q.id];
    if (Number(p?.seen || 0) > 0) n += 1;
  }
  return n;
});

const correctOnceCount = computed(() => {
  let n = 0;
  for (const q of store.questions || []) {
    const p = store.progress?.[q.id];
    if (Number(p?.correct || 0) > 0) n += 1;
  }
  return n;
});

const unansweredCount = computed(() => Math.max(0, totalQuestions.value - answeredCount.value));
const remainingToCorrectOnce = computed(() => Math.max(0, totalQuestions.value - correctOnceCount.value));

const incorrectEverCount = computed(() => {
  let n = 0;
  for (const q of store.questions || []) {
    const p = store.progress?.[q.id];
    if (Number(p?.wrong || 0) > 0) n += 1;
  }
  return n;
});

const totalAccuracy = computed(() => {
  let seen = 0;
  let correct = 0;
  for (const q of store.questions || []) {
    const p = store.progress?.[q.id];
    seen += Number(p?.seen || 0);
    correct += Number(p?.correct || 0);
  }
  if (seen <= 0) return null;
  return Math.round((correct / seen) * 100);
});

const correctOncePercent = computed(() => {
  if (totalQuestions.value <= 0) return null;
  return Math.round((correctOnceCount.value / totalQuestions.value) * 100);
});

const todayAccuracy = computed(() => {
  const seen = Number(store.daily?.seen || 0);
  const correct = Number(store.daily?.correct || 0);
  if (seen <= 0) return null;
  return Math.round((correct / seen) * 100);
});

const allSources = computed(() => {
  const counts = store.sourceCounts || {};
  const showSubject = subjectsList.value.length > 1;
  const items = [];
  subjectsList.value.forEach(sub => {
    sub.topics.forEach(topic => {
      const source = `${sub.name}/${topic}`;
      const count = counts[source] || 0;
      items.push({
        source,
        subject: sub.name,
        topic,
        count,
        label: showSubject ? `${formatName(sub.name)} — ${prettyTopic(topic)}` : `${prettyTopic(topic)}`,
      });
    });
  });

  // Non-empty first; empty at bottom (greyed out)
  return items.sort((a, b) => {
    const aEmpty = a.count === 0;
    const bEmpty = b.count === 0;
    if (aEmpty !== bEmpty) return aEmpty ? 1 : -1;
    return a.label.localeCompare(b.label, 'sv');
  });
});

// Format folder names (e.g. medical_exam -> Medical Exam)
const formatName = (str) => {
  return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Display overrides (filenames stay ASCII, UI can be Swedish)
const topicDisplayOverrides = {
  allmanmedicin: 'Allmänmedicin',
  oron_nasa_hals: 'Öron-näsa-hals',
};

const prettyTopic = (topic) => {
  const key = String(topic || '').replace(/\.ya?ml$/i, '');
  return topicDisplayOverrides[key] || formatName(key);
};

const startSpecific = (subject, topic) => {
  store.startSession('specific', `${subject}/${topic}`); // matches the 'source' field we added in bundle.py
};

const openCategoryPicker = () => {
  selectedSources.value = new Set();
  showCategoryPicker.value = true;
};

const closeCategoryPicker = () => {
  showCategoryPicker.value = false;
};

const toggleSource = (source) => {
  const next = new Set(selectedSources.value);
  if (next.has(source)) next.delete(source);
  else next.add(source);
  selectedSources.value = next;
};

const startSelected = (count) => {
  const sources = Array.from(selectedSources.value);
  if (sources.length === 0) {
    alert('Select at least one category.');
    return;
  }
  store.startSession('multi', sources, count);
  showCategoryPicker.value = false;
};

const focusSelected = (count) => {
  const sources = Array.from(selectedSources.value);
  if (sources.length === 0) {
    alert('Select at least one category.');
    return;
  }
  store.startSession('focus', sources, count);
  showCategoryPicker.value = false;
};
</script>

<template>
  <div class="space-y-8 p-4">
    <!-- Compact stats + quick actions (mobile-first) -->
    <section class="space-y-3">
      <div class="flex gap-2">
        <div class="flex-1 rounded-2xl border border-stone-200 bg-white/60 backdrop-blur px-4 py-3">
          <div class="text-xs text-stone-500">Correct at least once</div>
          <div class="mt-1 flex items-baseline gap-2">
            <div class="text-2xl font-extrabold text-emerald-700">
              {{ correctOncePercent === null ? '—' : (correctOncePercent + '%') }}
            </div>
            <div class="text-xs text-stone-500">
              {{ correctOnceCount }} / {{ totalQuestions }}
            </div>
          </div>
        </div>

        <div class="flex-1 rounded-2xl border border-stone-200 bg-white/60 backdrop-blur px-4 py-3">
          <div class="text-xs text-stone-500">Today</div>
          <div class="mt-1 flex items-baseline gap-2">
            <div class="text-2xl font-extrabold text-stone-900">
              {{ todayAccuracy === null ? '—' : (todayAccuracy + '%') }}
            </div>
            <div class="text-xs text-stone-500" v-if="totalAccuracy !== null">
              total {{ totalAccuracy }}%
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-2">
        <button
          @click="store.startSession('quick5')"
          class="rounded-2xl border border-indigo-100 bg-indigo-50/70 text-indigo-950 hover:bg-indigo-100/60 transition px-3 py-3"
        >
          <div class="text-lg font-extrabold">5Q</div>
          <div class="text-[11px] text-indigo-900/70">5 questions</div>
        </button>

        <button
          @click="store.startSession('quick10')"
          class="rounded-2xl border border-indigo-100 bg-indigo-50/70 text-indigo-950 hover:bg-indigo-100/60 transition px-3 py-3"
        >
          <div class="text-lg font-extrabold">10Q</div>
          <div class="text-[11px] text-indigo-900/70">10 questions</div>
        </button>

        <button
          @click="store.startSession('focus', null, 10)"
          class="rounded-2xl border border-emerald-100 bg-emerald-50/70 text-emerald-950 hover:bg-emerald-100/60 transition px-3 py-3"
        >
          <div class="text-lg font-extrabold">Focus</div>
          <div class="text-[11px] text-emerald-900/70">wrong-first</div>
        </button>
      </div>
    </section>

    <!-- Category Picker (multi-select) -->
    <section class="pt-1">

      <div v-if="subjectsList.length === 0" class="text-gray-500 italic">
        No content found. Please add content to /data folder.
      </div>

      <div v-else class="space-y-2">
        <button
          v-if="!showCategoryPicker"
          @click="openCategoryPicker"
          class="w-full p-4 bg-gradient-to-br from-stone-50 to-rose-50/50 border border-stone-200 rounded-xl hover:border-stone-300 transition text-left"
        >
          <div class="font-bold text-gray-800">Study specific categories</div>
          <div class="text-sm text-gray-500 mt-1">Pick categories</div>
        </button>

        <div v-else class="bg-white/70 backdrop-blur border border-stone-200 rounded-xl p-4">
          <div class="flex items-center justify-between mb-3">
            <div class="font-bold text-gray-800">Select categories</div>
            <button @click="closeCategoryPicker" class="text-sm text-gray-500 hover:text-gray-900">Cancel</button>
          </div>

          <div class="text-xs text-gray-500 mb-3">Selected: {{ selectedSources.size }}</div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-80 overflow-y-auto pr-1">
            <label
              v-for="item in allSources"
              :key="item.source"
              class="flex items-center gap-2 p-2 rounded-lg border border-gray-200 cursor-pointer"
              :class="item.count === 0 ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'hover:border-indigo-300 hover:bg-gray-50'"
            >
              <input
                type="checkbox"
                class="h-4 w-4"
                :checked="selectedSources.has(item.source)"
                :disabled="item.count === 0"
                @change="toggleSource(item.source)"
              />
              <span class="text-sm text-gray-800">{{ item.label }}</span>
              <span class="ml-auto text-xs text-gray-500" v-if="item.count !== 0">{{ item.count }}</span>
              <span class="ml-auto text-xs text-gray-400" v-else>0</span>
            </label>
          </div>

          <div class="mt-4 flex gap-2">
            <button
              @click="startSelected(5)"
              class="flex-1 py-2 px-3 rounded-lg bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition"
            >
              Start 5
            </button>
            <button
              @click="startSelected(10)"
              class="flex-1 py-2 px-3 rounded-lg bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition"
            >
              Start 10
            </button>
          </div>

          <div class="mt-2">
            <button
              @click="focusSelected(10)"
              class="w-full py-2 px-3 rounded-lg bg-emerald-700 text-white font-bold hover:bg-emerald-800 transition"
            >
              Focus (10)
            </button>
          </div>

          <div class="mt-3 text-xs text-gray-500">
            Tip: you can pick across subjects.
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
