import { defineStore } from 'pinia';
import { useStorage } from '@vueuse/core';

const randomFloat = () => {
  if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === 'function') {
    const buf = new Uint32Array(1);
    globalThis.crypto.getRandomValues(buf);
    return buf[0] / 0x100000000;
  }
  return Math.random();
};

const randomInt = (maxExclusive) => {
  if (maxExclusive <= 0) return 0;
  return Math.floor(randomFloat() * maxExclusive);
};

const shuffleInPlace = (arr) => {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
};

const takeRandom = (arr) => {
  const idx = randomInt(arr.length);
  return arr.splice(idx, 1)[0];
};

export const useStudyStore = defineStore('study', {
  state: () => ({
    loading: true,
    error: null,
    view: 'dashboard', // dashboard, quiz, summary
    
    // Data (Loaded from JSON)
    subjects: {}, // Structure: { folder: [ 'filename', ... ] }
    questions: [], // Flat list of all questions
    
    // Session State
    currentSession: [], // Array of question objects for current quiz
    currentIndex: 0,
    sessionAnswers: {}, // { questionId: { selected: 1, isCorrect: true } }
    
    // User Progress (Persisted in localStorage)
    // Structure: { questionId: { bucket: 'A'|'B'|'C', consecutiveCorrect: 0, lastSeen: timestamp, seen: 0, correct: 0, wrong: 0, lastWasCorrect: true|false } }
    progress: useStorage('iller5-progress', {}),

    // Daily accuracy tracking (local day)
    // Structure: { date: 'YYYY-MM-DD', seen: 0, correct: 0 }
    daily: useStorage('iller5-daily', { date: '', seen: 0, correct: 0 }),
  }),

  getters: {
    sourceCounts: (state) => {
      const counts = {};
      for (const q of state.questions) {
        if (!q?.source) continue;
        counts[q.source] = (counts[q.source] || 0) + 1;
      }
      return counts;
    },
  },

  actions: {
    ensureDaily() {
      const now = new Date();
      const yyyy = String(now.getFullYear());
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      const today = `${yyyy}-${mm}-${dd}`;

      if (!this.daily || typeof this.daily !== 'object') {
        this.daily = { date: today, seen: 0, correct: 0 };
        return;
      }

      if (this.daily.date !== today) {
        this.daily.date = today;
        this.daily.seen = 0;
        this.daily.correct = 0;
      }

      if (typeof this.daily.seen !== 'number') this.daily.seen = 0;
      if (typeof this.daily.correct !== 'number') this.daily.correct = 0;
    },
    async loadContent() {
      this.loading = true;
      try {
        // Use BASE_URL to handle GitHub Pages subdirectories correctly
        const baseUrl = import.meta.env.BASE_URL;
        // Ensure standard slash behavior
        const basePath = baseUrl.endsWith('/') ? `${baseUrl}content.json` : `${baseUrl}/content.json`;

        // Cache busting: GitHub Pages/static CDNs + browsers may cache content.json aggressively.
        // By varying the URL per deployment, we can fetch new questions without users clearing
        // site data (which would also wipe localStorage progress).
        const buildTag = (typeof __ILLER5_BUILD_TIME__ !== 'undefined' && __ILLER5_BUILD_TIME__)
          ? __ILLER5_BUILD_TIME__
          : `${Date.now()}`;
        const path = `${basePath}?v=${encodeURIComponent(buildTag)}`;
        
        const response = await fetch(path, { cache: 'no-store' });
        if (!response.ok) throw new Error("Failed to load content.json");
        
        const data = await response.json();
        this.subjects = data.subjects;
        this.questions = data.questions;
        
        // Sanitize progress (remove IDs that don't exist anymore if needed, or just ignore them)
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    startSession(mode, target = null, countOverride = null) {
      // mode: 'quick5', 'quick10', 'focus', 'specific', 'multi'
      // target: string source (e.g. 'medical_exam/kardiologi') or array of sources
      
      let candidateQuestions = [];

      if (typeof target === 'string' && target) {
        candidateQuestions = this.questions.filter(q => q.source === target);
      } else if (Array.isArray(target) && target.length > 0) {
        const selected = new Set(target);
        candidateQuestions = this.questions.filter(q => selected.has(q.source));
      } else {
        candidateQuestions = this.questions;
      }

      if (candidateQuestions.length === 0) {
        alert("No questions found for this selection.");
        return;
      }

      const count = (typeof countOverride === 'number' && Number.isFinite(countOverride))
        ? Math.max(1, Math.floor(countOverride))
        : ((mode === 'quick5') ? 5 : 10);

      this.currentSession = (mode === 'focus')
        ? this.selectQuestionsFocus(candidateQuestions, count)
        : this.selectQuestionsSRS(candidateQuestions, count);
      this.currentIndex = 0;
      this.sessionAnswers = {};
      this.view = 'quiz';
    },

    selectQuestionsSRS(candidates, count) {
      if (candidates.length <= count) return shuffleInPlace([...candidates]);

      // Group by buckets
      const buckets = { A: [], B: [], C: [] };
      
      candidates.forEach(q => {
        const p = this.progress[q.id];
        if (!p) {
          buckets.A.push(q); // New = Bucket A
        } else {
          buckets[p.bucket].push(q);
        }
      });

      // Weighted draw (70/20/10) per slot for a more natural/random session order.
      // Still heavily favors Bucket A, but avoids "sticky" ordering from sort-random shuffles.
      const weights = { A: 0.7, B: 0.2, C: 0.1 };

      const selected = [];
      while (selected.length < count) {
        const available = ['A', 'B', 'C'].filter(k => buckets[k].length > 0);
        if (available.length === 0) break;

        const totalWeight = available.reduce((sum, k) => sum + weights[k], 0);
        let r = randomFloat() * totalWeight;
        let chosen = available[0];
        for (const k of available) {
          r -= weights[k];
          if (r <= 0) {
            chosen = k;
            break;
          }
        }

        selected.push(takeRandom(buckets[chosen]));
      }

      // Backfill if needed (should only happen if candidates were mutated unexpectedly)
      if (selected.length < count) {
        const alreadySelectedIds = new Set(selected.map(q => q.id));
        const remaining = candidates.filter(q => !alreadySelectedIds.has(q.id));
        shuffleInPlace(remaining);
        selected.push(...remaining.slice(0, count - selected.length));
      }

      return selected;
    },

    selectQuestionsFocus(candidates, count) {
      // Focus mode: prefer questions the user got wrong (especially last time),
      // then backfill with SRS if there aren't enough.
      const now = Date.now();

      const scored = candidates.map(q => {
        const p = this.progress[q.id];
        const seen = Number(p?.seen || 0);
        const wrong = Number(p?.wrong || 0);
        const correct = Number(p?.correct || 0);
        const lastWasCorrect = (typeof p?.lastWasCorrect === 'boolean') ? p.lastWasCorrect : null;
        const lastSeen = Number(p?.lastSeen || 0);
        const wrongRate = seen > 0 ? (wrong / seen) : 0;
        const recentBoost = lastSeen > 0 ? Math.max(0, 1 - (now - lastSeen) / (1000 * 60 * 60 * 24 * 14)) : 0;

        // Large base for having any wrong history; extra for being wrong last time.
        let score = 0;
        if (seen > 0) score += 1;
        if (wrong > 0) score += 1000;
        score += wrongRate * 200;
        if (lastWasCorrect === false) score += 250;
        score += recentBoost * 50;

        // Tie-breaker jitter so the same "worst" set doesn't always start identical.
        score += randomFloat() * 0.5;

        return { q, score, wrong, seen, correct };
      });

      // Prefer questions with wrong history first.
      scored.sort((a, b) => b.score - a.score);
      const focusPool = scored
        .filter(x => (x.seen > 0 && x.wrong > 0) || (this.progress[x.q.id]?.lastWasCorrect === false))
        .map(x => x.q);

      const picked = focusPool.slice(0, Math.min(count, focusPool.length));
      if (picked.length >= count) return picked;

      // Backfill with SRS selection from remaining candidates.
      const already = new Set(picked.map(q => q.id));
      const remaining = candidates.filter(q => !already.has(q.id));
      const backfill = this.selectQuestionsSRS(remaining, count - picked.length);
      return picked.concat(backfill);
    },

    recordAnswer(questionId, isCorrect) {
      // Update Progress
      let p = this.progress[questionId] || {
        bucket: 'A',
        consecutiveCorrect: 0,
        lastSeen: 0,
        seen: 0,
        correct: 0,
        wrong: 0,
        lastWasCorrect: true,
      };

      // Normalize older entries
      if (typeof p.seen !== 'number') p.seen = 0;
      if (typeof p.correct !== 'number') p.correct = 0;
      if (typeof p.wrong !== 'number') p.wrong = 0;
      if (typeof p.lastWasCorrect !== 'boolean') p.lastWasCorrect = true;

      // Daily stats
      this.ensureDaily();
      this.daily.seen += 1;
      if (isCorrect) this.daily.correct += 1;
      
      if (isCorrect) {
        p.consecutiveCorrect += 1;
        p.correct += 1;
        p.lastWasCorrect = true;
        // Promote logic
        // A -> Correct once -> B
        // B -> Correct again (total 2) -> C
        if (p.bucket === 'A') p.bucket = 'B';
        else if (p.bucket === 'B') p.bucket = 'C';
        // C stays C
      } else {
        // Wrong -> Back to A
        p.bucket = 'A';
        p.consecutiveCorrect = 0;
        p.wrong += 1;
        p.lastWasCorrect = false;
      }

      p.seen += 1;
      
      p.lastSeen = Date.now();
      this.progress[questionId] = p;
    }
  }
});
