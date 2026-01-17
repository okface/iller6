<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { useStudyStore } from '@/stores/study';

const store = useStudyStore();

// Local state for the current card interaction
const answered = ref(false);
const selectedOptionIndex = ref(null); 
const revealedOptions = ref(new Set()); // Track which options user clicked AFTER answering
const optionOrder = ref([]); // Array of original option indices, shuffled per question
const questionHeaderRef = ref(null);

const tagColors = [
  'text-blue-700 bg-blue-50 border-blue-100',
  'text-emerald-700 bg-emerald-50 border-emerald-100',
  'text-purple-700 bg-purple-50 border-purple-100',
  'text-rose-700 bg-rose-50 border-rose-100',
  'text-amber-700 bg-amber-50 border-amber-100',
  'text-cyan-700 bg-cyan-50 border-cyan-100',
  'text-indigo-700 bg-indigo-50 border-indigo-100',
];

const getTagClass = (tag) => {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % tagColors.length;
  return tagColors[index];
};

const randomInt = (maxExclusive) => {
  if (maxExclusive <= 0) return 0;
  if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === 'function') {
    const buf = new Uint32Array(1);
    globalThis.crypto.getRandomValues(buf);
    return buf[0] % maxExclusive;
  }
  return Math.floor(Math.random() * maxExclusive);
};

const shuffleInPlace = (arr) => {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
};

// Current Question Data
const currentQuestion = computed(() => {
  if (!store.currentSession || store.currentSession.length === 0) return null;
  return store.currentSession[store.currentIndex];
});

const displayOptions = computed(() => {
  if (!currentQuestion.value) return [];
  const opts = currentQuestion.value.options || [];
  if (!Array.isArray(opts) || opts.length === 0) return [];
  if (!Array.isArray(optionOrder.value) || optionOrder.value.length !== opts.length) {
    return opts;
  }
  return optionOrder.value.map(i => opts[i]);
});

const formatName = (str) => {
  return String(str || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const topicDisplayOverrides = {
  allmanmedicin: 'Allmänmedicin',
  oron_nasa_hals: 'Öron-näsa-hals',
};

const prettyTopic = (topic) => {
  const key = String(topic || '');
  return topicDisplayOverrides[key] || formatName(key);
};

const sourceLabel = computed(() => {
  const src = currentQuestion.value?.source;
  if (!src) return '';
  const parts = String(src).split('/');
  // If the app currently has only one subject folder, just show the topic.
  const hasMultipleSubjects = Object.keys(store.subjects || {}).length > 1;
  if (!hasMultipleSubjects && parts.length >= 2) return prettyTopic(parts.slice(1).join('/'));
  if (parts.length >= 2) return `${formatName(parts[0])} / ${prettyTopic(parts.slice(1).join('/'))}`;
  return formatName(parts.join(' / '));
});

const scrollQuestionIntoView = async () => {
  await nextTick();
  // Scroll to the question text, with a slight offset if possible (or just top)
  // block: 'start' aligns the top of element with top of viewport
  questionHeaderRef.value?.scrollIntoView({ block: 'start', behavior: 'auto' });
};

// Progress
const progressText = computed(() => {
  return `${store.currentIndex + 1} / ${store.currentSession.length}`;
});

const isFinished = computed(() => {
  return store.currentIndex >= store.currentSession.length;
});

// Watch for question change to reset local state
watch(
  () => currentQuestion.value?.id,
  () => {
  answered.value = false;
  selectedOptionIndex.value = null;
  revealedOptions.value = new Set();

  const n = currentQuestion.value?.options?.length || 0;
  optionOrder.value = shuffleInPlace(Array.from({ length: n }, (_, i) => i));

  scrollQuestionIntoView();
  },
  { immediate: true }
);

// Actions
const selectOption = (index) => {
  // If already answered, just reveal this option's feedback (The "Why" feature)
  if (answered.value) {
    if (index !== selectedOptionIndex.value) {
        revealedOptions.value.add(index);
    }
    return;
  }

  // First selection (The actual answer)
  selectedOptionIndex.value = index;
  answered.value = true;
  
  // Check correctness
  const originalIndex = optionOrder.value[index] ?? index;
  const isCorrect = currentQuestion.value.options[originalIndex].correct;
  
  // Record in store
  store.recordAnswer(currentQuestion.value.id, isCorrect);
};

const nextQuestion = () => {
  if (store.currentIndex < store.currentSession.length - 1) {
    store.currentIndex++;
    // scroll handled by watcher, but keep this for extra safety
    scrollQuestionIntoView();
  } else {
    // End session
    store.view = 'dashboard';
    store.currentSession = [];
    store.currentIndex = 0;
  }
};

// Styles for options
const getOptionClass = (index, option) => {
  const base = "w-full p-3 mb-2 text-left border rounded-lg transition-all duration-200 relative ";
  
  if (!answered.value) {
    return base + "bg-white border-gray-200 hover:border-indigo-500 hover:bg-gray-50";
  }

  // Answered State Logic
  const isSelected = index === selectedOptionIndex.value;
  const isCorrect = option.correct;

  if (isCorrect) {
    // ALWAYS show Green for correct answer
    return base + "bg-green-50 border-green-500 ring-1 ring-green-500";
  }
  
  if (isSelected && !isCorrect) {
    // Show Red for selected wrong answer
    return base + "bg-red-50 border-red-500 ring-1 ring-red-500";
  }

  // Unselected, Incorrect options
  return base + "bg-gray-50 border-gray-200 opacity-75 cursor-pointer hover:bg-gray-100";
};

</script>

<template>
  <div v-if="currentQuestion" class="max-w-2xl mx-auto pb-32">
    
    <!-- Top Bar (Quit, Metadata, Counter) -->
    <div class="flex flex-wrap justify-between items-center mb-6 pt-2 text-xs text-stone-500 border-b border-stone-100 pb-2">
      <!-- Quit -->
      <button @click="store.view = 'dashboard'" class="hover:text-red-700 hover:underline font-bold mr-3 text-xs">
        &larr; Quit
      </button>

      <!-- Center: Category / Tags -->
      <div class="flex-grow flex flex-col md:flex-row items-center justify-center text-[11px] gap-x-2 leading-tight">
         <span v-if="sourceLabel" class="font-semibold text-slate-500">{{ sourceLabel }}</span>
         <span v-if="sourceLabel && currentQuestion.tags.length" class="hidden md:inline text-slate-300">|</span>
         <div class="flex flex-wrap justify-center gap-1 mt-1 md:mt-0">
             <span v-for="tag in currentQuestion.tags" :key="tag" 
                class="inline-block text-[10px] font-bold px-2 py-0.5 rounded border"
                :class="getTagClass(tag)">
                 {{ tag }}
             </span>
         </div>
      </div>
      
      <!-- Counter -->
      <span class="ml-3 bg-stone-100 px-2 py-1 rounded text-stone-600 font-mono text-[10px]">{{ progressText }}</span>
    </div>

    <!-- Question Text (Target for Scroll) -->
    <h2 ref="questionHeaderRef" class="text-lg font-bold text-gray-900 leading-snug mb-6">
      {{ currentQuestion.question }}
    </h2>

    <!-- Image (if any) -->
    <div v-if="currentQuestion.image" class="mb-6 rounded-lg overflow-hidden border border-gray-200 shadow-sm">
      <img :src="currentQuestion.image" alt="Question Image" class="w-full h-auto object-cover max-h-80" />
    </div>

    <!-- Options -->
    <div class="mb-3">
      <button 
        v-for="(opt, idx) in displayOptions" 
        :key="idx"
        @click="selectOption(idx)"
        :class="getOptionClass(idx, opt)"
      >
        <div class="flex items-start">
            <span class="flex-shrink-0 w-6 h-6 rounded-full border flex items-center justify-center text-xs mr-3 mt-0.5 transition-colors"
                :class="
                  answered 
                  ? (opt.correct ? 'border-green-500 bg-green-500 text-white font-bold' : (idx === selectedOptionIndex ? 'border-red-500 bg-red-500 text-white font-bold' : 'border-gray-300 text-gray-400'))
                  : 'border-gray-300 text-gray-500 group-hover:border-indigo-400'
                ">
                {{ String.fromCharCode(65 + idx) }}
            </span>
            <span class="text-stone-800 text-base leading-relaxed text-left">{{ opt.text }}</span>
        </div>

        <!-- Post-Answer Feedback (The "Why" Feature) -->
        <!-- Logic: Show if (Answered AND (IsSelected OR IsCorrect OR Revealed)) -->
        <div 
          v-if="answered && (idx === selectedOptionIndex || opt.correct || revealedOptions.has(idx))" 
          class="mt-1 pl-10 text-sm italic"
          :class="opt.correct ? 'text-green-700' : 'text-red-700'"
        >
          <span v-if="opt.correct" class="font-bold not-italic mr-1">Correct:</span>
          <span v-else class="font-bold not-italic mr-1">Wrong:</span>
          {{ opt.feedback }}
        </div>
      </button>
    </div>

    <!-- General Explanation (Always appears after answer) -->
    <div v-if="answered" class="p-3 bg-amber-50/50 border border-amber-100/50 rounded-lg mb-4 animate-fade-in shadow-sm">
      <h3 class="text-xs font-bold text-amber-900/40 mb-2 uppercase tracking-widest">Explanation</h3>
      <p class="text-stone-800 text-sm leading-relaxed">
        {{ currentQuestion.explanation }}
      </p>
    </div>

    <!-- Next Button (Fixed Bottom) -->
    <div v-if="answered" class="fixed bottom-0 left-0 right-0 p-3 bg-white/95 backdrop-blur border-t border-stone-200 z-50 flex justify-center shadow-lg">
      <div class="w-full max-w-2xl px-4 md:px-6">
        <button 
          @click="nextQuestion"
          class="w-full bg-slate-900 hover:bg-slate-800 text-white text-base py-3 rounded-lg font-bold shadow transform active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
        >
          <span>{{ store.currentIndex < store.currentSession.length - 1 ? 'Next Question' : 'Finish Session' }}</span>
          <span>&rarr;</span>
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
