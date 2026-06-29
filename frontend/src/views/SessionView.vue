<script setup>
import { ref, onUnmounted } from "vue";
import AppLayout from "../layouts/AppLayout.vue";

// ── Flow state ────────────────────────────────────────────────
const sessionState = ref("setup"); // 'setup' | 'starting' | 'active'
const selectedClass = ref("IT 301 — Data Structures");
const uploadedFile = ref(null);
const uploadStatus = ref("idle"); // 'idle' | 'processing' | 'ready'
const startingStep = ref(0);
const fileInput = ref(null);

const startingSteps = [
  "Initializing camera feeds...",
  "Connecting engagement sensors...",
  "Loading presentation slides...",
  "Starting live monitoring...",
];

const monitoringSettings = ref([
  { label: "Real-time face tracking", enabled: true },
  { label: "Engagement detection", enabled: true },
  { label: "Live alert notifications", enabled: true },
  { label: "Record session video", enabled: false },
]);

const rosterPreview = [
  { initials: "MR", color: "#2D3CC8" },
  { initials: "JC", color: "#3A4FD4" },
  { initials: "AL", color: "#465FF1" },
  { initials: "RC", color: "#1E35A8" },
  { initials: "SG", color: "#465FF1" },
  { initials: "BT", color: "#2F42C0" },
  { initials: "LV", color: "#2D3CC8" },
  { initials: "KD", color: "#3A4FD4" },
];

const triggerUpload = () => fileInput.value?.click();

const handleFile = (file) => {
  if (!file) return;
  uploadedFile.value = file;
  uploadStatus.value = "processing";
  setTimeout(() => {
    uploadStatus.value = "ready";
  }, 1800);
};

const onFileInput = (e) => handleFile(e.target.files[0]);
const onDrop = (e) => {
  e.preventDefault();
  handleFile(e.dataTransfer.files[0]);
};
const onDragOver = (e) => e.preventDefault();

const startSession = () => {
  sessionState.value = "starting";
  startingStep.value = 0;
  const iv = setInterval(() => {
    if (startingStep.value < startingSteps.length - 1) {
      startingStep.value++;
    } else {
      clearInterval(iv);
      setTimeout(() => {
        sessionState.value = "active";
        beginTimer();
      }, 700);
    }
  }, 700);
};

// ── Timer ─────────────────────────────────────────────────────
const timerDisplay = ref("00:00");
let seconds = 0;
let timerInterval = null;

const beginTimer = () => {
  seconds = 0;
  timerInterval = setInterval(() => {
    seconds++;
    timerDisplay.value = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }, 1000);
};
onUnmounted(() => clearInterval(timerInterval));

// ── Slides ────────────────────────────────────────────────────
const slideTopics = [
  "Introduction to Trees",
  "Tree Terminology",
  "Binary Trees Defined",
  "Tree Representation",
  "Binary Trees & Traversal",
  "Inorder Traversal",
  "Preorder Traversal",
  "Postorder Traversal",
  "Binary Search Trees",
  "BST Operations",
  "Tree Balancing Intro",
  "Summary & Q&A",
];
const slideContent = [
  [
    "What is a Tree data structure?",
    "Hierarchical organization of nodes",
    "Connected via edges with no cycles",
    "Root, parent, child relationships",
  ],
  [
    "Node — basic unit of a tree",
    "Root — topmost node",
    "Leaf — node with no children",
    "Edge — connection between nodes",
  ],
  [
    "Each node has at most 2 children",
    "Left subtree and right subtree",
    "An empty tree is also a binary tree",
    "Used in search, sort, and expression trees",
  ],
  [
    "Array-based vs linked representation",
    "Parent at i, children at 2i+1 and 2i+2",
    "Trade-offs: space vs. traversal speed",
    "Common in competitive programming",
  ],
  [
    "Three main traversal orders exist",
    "Inorder: Left → Root → Right",
    "Preorder: Root → Left → Right",
    "Postorder: Left → Right → Root",
  ],
  [
    "Inorder visits left subtree first",
    "Then the root node",
    "Then the right subtree",
    "Produces sorted output for BST",
  ],
  [
    "Preorder visits root first",
    "Then left subtree",
    "Then right subtree",
    "Useful for copying tree structure",
  ],
  [
    "Postorder visits left subtree first",
    "Then right subtree",
    "Root is visited last",
    "Used for deleting or evaluating trees",
  ],
  [
    "Left child < Parent < Right child",
    "Average search time: O(log n)",
    "Worst case (skewed): O(n)",
    "Foundation for balanced tree variants",
  ],
  [
    "Insert: traverse until empty spot",
    "Delete: leaf / one child / two children cases",
    "Search: compare and go left or right",
    "All operations: O(h) where h = height",
  ],
  [
    "Unbalanced BST degrades to O(n)",
    "AVL trees maintain height ≤ log n",
    "Balance factor = height(left) − height(right)",
    "Rotations restore balance after operations",
  ],
  [
    "Trees model hierarchical relationships",
    "Traversal strategy depends on use case",
    "BST enables efficient ordered operations",
    "Next: Graph structures and algorithms",
  ],
];

const currentSlide = ref(1);
const showCameras = ref(false);
const prevSlide = () => {
  if (currentSlide.value > 1) currentSlide.value--;
};
const nextSlide = () => {
  if (currentSlide.value < slideTopics.length) currentSlide.value++;
};

// ── Alerts & students ─────────────────────────────────────────
const alerts = ref([
  {
    id: 1,
    type: "danger",
    title: "Disengagement Spike",
    msg: "5 students disengaged on Slide 4",
  },
  {
    id: 2,
    type: "warning",
    title: "High Confusion",
    msg: "8 students showing confusion signals",
  },
  {
    id: 3,
    type: "danger",
    title: "Boredom Detected",
    msg: "3 students showing boredom indicators",
  },
]);
const dismissAlert = (id) => {
  alerts.value = alerts.value.filter((a) => a.id !== id);
};

const students = [
  { initials: "MR", name: "Maria Reyes", status: "Engaged" },
  { initials: "JC", name: "Juan Cruz", status: "Confused" },
  { initials: "AL", name: "Ana Lim", status: "Engaged" },
  { initials: "RC", name: "Ramon Capili", status: "Disengaged" },
  { initials: "SG", name: "Sofia Garcia", status: "Attentive" },
  { initials: "BT", name: "Ben Torres", status: "Bored" },
  { initials: "LV", name: "Lena Villanueva", status: "Engaged" },
  { initials: "KD", name: "Kyle Diaz", status: "Confused" },
];
const donutLegend = [
  { label: "Engaged", pct: 62, color: "#2D3CC8" },
  { label: "Attentive", pct: 10, color: "#10B981" },
  { label: "Confused", pct: 18, color: "#F59E0B" },
  { label: "Bored", pct: 6, color: "#F97316" },
  { label: "Disengaged", pct: 4, color: "#EF476F" },
];
const badgeClass = (s) =>
  ({
    Engaged: "badge-engaged",
    Attentive: "badge-attentive",
    Confused: "badge-confused",
    Bored: "badge-bored",
    Disengaged: "badge-disengaged",
  })[s] || "badge-bored";
const avatarColor = (s) =>
  ({
    Engaged: "#2D3CC8",
    Attentive: "#465FF1",
    Confused: "#3A4FD4",
    Bored: "#2F42C0",
    Disengaged: "#1E35A8",
  })[s] || "#465FF1";

const showEngagement = ref(true);
</script>

<template>
  <AppLayout
    :page-title="
      sessionState === 'active'
        ? 'Live Monitoring Session'
        : 'Start New Session'
    "
    :focus-mode="sessionState === 'active'"
  >
    <!-- ══════════════════════════════════════════════════
         STATE 1 — SETUP
    ══════════════════════════════════════════════════ -->
    <div v-if="sessionState === 'setup'">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Left: Session details + upload -->
        <div class="lg:col-span-2 space-y-5">
          <!-- Session details -->
          <div class="page-card p-6">
            <h3
              class="text-sm font-semibold text-navy mb-4 flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4 text-brand"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
                />
              </svg>
              Session Details
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label
                  for="session-class"
                  class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide"
                  >Class</label
                >
                <select
                  id="session-class"
                  v-model="selectedClass"
                  class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-navy"
                  @focus="$event.target.style.borderColor = '#465FF1'"
                  @blur="$event.target.style.borderColor = '#e2e8f0'"
                >
                  <option>IT 301 — Data Structures</option>
                  <option>IT 302 — Database Management</option>
                  <option>IT 303 — Operating Systems</option>
                </select>
              </div>
              <div>
                <label
                  for="session-room"
                  class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide"
                  >Room</label
                >
                <input
                  id="session-room"
                  type="text"
                  value="Room 201 — Lab A"
                  class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-navy"
                  @focus="$event.target.style.borderColor = '#465FF1'"
                  @blur="$event.target.style.borderColor = '#e2e8f0'"
                />
              </div>
              <div>
                <label
                  for="session-date"
                  class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide"
                  >Date</label
                >
                <input
                  id="session-date"
                  type="text"
                  value="June 26, 2026"
                  class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-gray-400"
                  readonly
                />
              </div>
              <div>
                <label
                  for="session-time"
                  class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide"
                  >Time</label
                >
                <input
                  id="session-time"
                  type="text"
                  value="10:30 AM"
                  class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-gray-400"
                  readonly
                />
              </div>
            </div>
          </div>

          <!-- Upload presentation -->
          <div class="page-card p-6">
            <h3
              class="text-sm font-semibold text-navy mb-4 flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4 text-brand"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3"
                />
              </svg>
              Upload Presentation
            </h3>
            <label for="file-upload" class="sr-only"
              >Upload presentation file</label
            >
            <input
              ref="fileInput"
              id="file-upload"
              type="file"
              accept=".ppt,.pptx,.pdf"
              class="hidden"
              @change="onFileInput"
            />

            <!-- Idle / drop zone -->
            <div
              v-if="uploadStatus === 'idle'"
              class="border-2 border-dashed border-gray-200 rounded-xl p-10 text-center cursor-pointer hover:border-brand hover:bg-brand-light transition-colors"
              @click="triggerUpload"
              @drop="onDrop"
              @dragover="onDragOver"
            >
              <div
                class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
                style="background: rgba(70, 95, 241, 0.1)"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-6 h-6 text-brand"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="1.8"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                  />
                </svg>
              </div>
              <p class="text-sm font-semibold text-navy mb-1">
                Drag & drop your slides here
              </p>
              <p class="text-xs text-gray-400 mb-4">Supports PPT, PPTX, PDF</p>
              <button
                class="btn-primary text-xs px-4 py-2"
                @click.stop="triggerUpload"
              >
                Browse Files
              </button>
            </div>

            <!-- Processing -->
            <div
              v-else-if="uploadStatus === 'processing'"
              class="border-2 border-dashed border-brand rounded-xl p-10 text-center"
              style="background: rgba(70, 95, 241, 0.03)"
            >
              <div
                class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
                style="background: rgba(70, 95, 241, 0.1)"
              >
                <svg
                  class="w-6 h-6 text-brand animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              </div>
              <p class="text-sm font-semibold text-navy mb-1">
                Processing slides…
              </p>
              <p class="text-xs text-gray-400">{{ uploadedFile?.name }}</p>
            </div>

            <!-- Ready -->
            <div
              v-else
              class="border-2 border-green-200 rounded-xl p-5"
              style="background: rgba(34, 197, 94, 0.04)"
            >
              <div class="flex items-center gap-3 mb-4">
                <div
                  class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style="background: rgba(34, 197, 94, 0.12)"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="#16a34a"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="m4.5 12.75 6 6 9-13.5"
                    />
                  </svg>
                </div>
                <div class="flex-1">
                  <p class="text-sm font-semibold text-navy">
                    {{ uploadedFile?.name }}
                  </p>
                  <p class="text-xs text-gray-400 mt-0.5">
                    12 slides detected · Ready to present
                  </p>
                </div>
                <button
                  class="text-xs text-gray-400 hover:text-gray-600 underline"
                  @click="
                    uploadStatus = 'idle';
                    uploadedFile = null;
                  "
                >
                  Remove
                </button>
              </div>
              <!-- Slide thumbnails strip -->
              <div class="flex gap-2 overflow-x-auto pb-1">
                <div
                  v-for="n in 12"
                  :key="n"
                  class="flex-shrink-0 w-20 rounded-lg overflow-hidden border-2 transition-colors cursor-pointer"
                  :class="
                    n === currentSlide ? 'border-brand' : 'border-transparent'
                  "
                  @click="currentSlide = n"
                  style="
                    aspect-ratio: 16/9;
                    background: linear-gradient(135deg, #1d2a3b, #0f1e35);
                  "
                >
                  <div
                    class="w-full h-full flex flex-col items-center justify-center p-1"
                  >
                    <span
                      class="text-white font-bold"
                      style="font-size: 10px"
                      >{{ n }}</span
                    >
                    <span
                      class="text-gray-500 text-center leading-tight"
                      style="font-size: 7px"
                      >{{
                        slideTopics[n - 1].split(" ").slice(0, 2).join(" ")
                      }}</span
                    >
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Roster + settings -->
        <div class="space-y-5">
          <!-- Class info -->
          <div class="page-card p-5">
            <h3 class="text-sm font-semibold text-navy mb-3 flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 3.741-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" />
              </svg>
              Class Info
            </h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between py-2 border-b border-gray-50">
                <span class="text-xs text-gray-400">Class</span>
                <span class="text-xs font-semibold text-navy">{{ selectedClass.split("—")[0].trim() }}</span>
              </div>
              <div class="flex items-center justify-between py-2 border-b border-gray-50">
                <span class="text-xs text-gray-400">Subject</span>
                <span class="text-xs font-semibold text-navy">{{ selectedClass.split("—")[1]?.trim() || "—" }}</span>
              </div>
              <div class="flex items-center justify-between py-2">
                <span class="text-xs text-gray-400">Students Enrolled</span>
                <span class="text-xs font-semibold text-navy">34 students</span>
              </div>
            </div>
            <RouterLink to="/students" class="text-xs font-medium text-brand mt-3 block">View class details →</RouterLink>
          </div>

          <!-- Monitoring settings -->
          <div class="page-card p-5">
            <h3
              class="text-sm font-semibold text-navy mb-4 flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-4 h-4 text-brand"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                />
              </svg>
              Monitoring Settings
            </h3>
            <div class="space-y-3">
              <label
                v-for="s in monitoringSettings"
                :key="s.label"
                class="flex items-center justify-between cursor-pointer"
              >
                <span class="text-sm text-gray-600">{{ s.label }}</span>
                <div class="relative w-9 h-5 flex-shrink-0">
                  <input type="checkbox" v-model="s.enabled" class="sr-only" />
                  <div
                    class="w-9 h-5 rounded-full transition-colors"
                    :style="{ background: s.enabled ? '#465FF1' : '#e2e8f0' }"
                  ></div>
                  <div
                    class="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform pointer-events-none"
                    :style="{
                      transform: s.enabled
                        ? 'translateX(16px)'
                        : 'translateX(0)',
                    }"
                  ></div>
                </div>
              </label>
            </div>
          </div>

          <!-- Start button -->
          <button
            @click="startSession"
            :disabled="!selectedClass"
            class="btn-primary w-full justify-center py-3 text-sm rounded-xl disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
              />
            </svg>
            Start Live Session
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════
         STATE 2 — STARTING ANIMATION
    ══════════════════════════════════════════════════ -->
    <div
      v-else-if="sessionState === 'starting'"
      class="flex items-center justify-center min-h-96"
    >
      <div class="text-center max-w-sm">
        <div
          class="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
          style="background: rgba(70, 95, 241, 0.1)"
        >
          <svg
            class="w-10 h-10 text-brand animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
        <h2 class="text-xl font-bold text-navy mb-2">Starting Session</h2>
        <p class="text-sm text-gray-400 mb-8">{{ selectedClass }}</p>
        <div class="space-y-3 text-left">
          <div
            v-for="(step, idx) in startingSteps"
            :key="idx"
            class="flex items-center gap-3 text-sm transition-all"
            :class="idx <= startingStep ? 'text-navy' : 'text-gray-300'"
          >
            <div
              class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
              :style="
                idx < startingStep
                  ? 'background:#16a34a'
                  : idx === startingStep
                    ? 'background:#465FF1'
                    : 'background:#e5e7eb'
              "
            >
              <svg
                v-if="idx < startingStep"
                xmlns="http://www.w3.org/2000/svg"
                class="w-3 h-3 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="3"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="m4.5 12.75 6 6 9-13.5"
                />
              </svg>
              <span
                v-else-if="idx === startingStep"
                class="w-2 h-2 bg-white rounded-full animate-pulse block"
              ></span>
            </div>
            {{ step }}
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════
         STATE 3 — ACTIVE SESSION
    ══════════════════════════════════════════════════ -->
    <div v-else class="flex flex-col gap-5">
      <!-- Status bar — white card -->
      <div class="page-card px-5 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div class="flex flex-wrap items-center gap-4 sm:gap-5">
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full" style="background:rgba(239,71,111,0.08);">
            <span class="w-2 h-2 rounded-full animate-pulse bg-danger"></span>
            <span class="text-xs font-bold text-danger">LIVE</span>
          </div>
          <span class="font-semibold text-sm text-navy">{{ selectedClass }}</span>
          <div class="h-5 w-px bg-gray-100 hidden sm:block"></div>
          <div class="hidden sm:flex items-center gap-1.5 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>
            <span class="text-xs font-mono font-semibold">{{ timerDisplay }}</span>
          </div>
          <div class="hidden md:flex items-center gap-1.5 text-xs text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3"/></svg>
            Slide {{ currentSlide }} / {{ slideTopics.length }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors"
            :class="showCameras ? 'border-brand text-brand bg-brand-light' : 'border-gray-200 text-gray-500 hover:border-gray-300'"
            @click="showCameras = !showCameras">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/></svg>
            <span class="hidden sm:inline">Cameras</span>
          </button>
          <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors"
            :class="showEngagement ? 'border-brand text-brand bg-brand-light' : 'border-gray-200 text-gray-500 hover:border-gray-300'"
            @click="showEngagement = !showEngagement">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"/></svg>
            <span class="hidden sm:inline">Engagement</span>
          </button>
          <div class="w-px h-5 bg-gray-200 mx-1"></div>
          <RouterLink to="/analytics" class="btn-danger text-xs">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 7.5A2.25 2.25 0 0 1 7.5 5.25h9a2.25 2.25 0 0 1 2.25 2.25v9a2.25 2.25 0 0 1-2.25 2.25h-9a2.25 2.25 0 0 1-2.25-2.25v-9Z"/></svg>
            End Session
          </RouterLink>
        </div>
      </div>

      <!-- Content: slide + engagement panel -->
      <div class="flex gap-5 items-start">
        <!-- Left: slide + cameras -->
        <div
          class="flex-1 min-w-0 flex flex-col gap-4"
        >
          <div class="page-card overflow-hidden">
            <div class="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3"/></svg>
                <span class="text-sm font-semibold text-navy">Slide Presentation</span>
                <span v-if="uploadedFile" class="text-xs text-gray-400">· {{ uploadedFile.name }}</span>
              </div>
              <span class="text-xs text-gray-400">Started 10:30 AM</span>
            </div>
            <div class="p-4">
            <!-- Slide -->
            <div
              class="relative rounded-xl overflow-hidden"
              style="
                aspect-ratio: 16/9;
                background: linear-gradient(135deg, #0f1e35 0%, #1d2a3b 100%);
              "
            >
              <!-- Engagement bar across top -->
              <div class="absolute top-0 left-0 right-0 h-1 flex">
                <div
                  style="width: 62%; background: #2d3cc8"
                  class="h-full"
                ></div>
                <div
                  style="width: 18%; background: #7b92f5"
                  class="h-full"
                ></div>
                <div
                  style="width: 12%; background: #a8bcfa"
                  class="h-full"
                ></div>
                <div
                  style="width: 8%; background: #c8d5fb"
                  class="h-full"
                ></div>
              </div>
              <!-- Content -->
              <div
                class="absolute inset-0 flex flex-col justify-center px-12 py-10"
              >
                <div
                  class="text-xs font-semibold uppercase tracking-widest mb-4"
                  style="color: rgba(70, 95, 241, 0.8)"
                >
                  {{ selectedClass }}
                </div>
                <h2
                  class="text-3xl lg:text-4xl font-bold text-white mb-7 leading-tight"
                >
                  {{ slideTopics[currentSlide - 1] }}
                </h2>
                <ul class="space-y-3">
                  <li
                    v-for="(point, idx) in slideContent[currentSlide - 1]"
                    :key="idx"
                    class="flex items-start gap-3"
                    :style="{
                      color:
                        idx === 0
                          ? 'rgba(255,255,255,0.9)'
                          : 'rgba(255,255,255,0.5)',
                      fontSize: '0.95rem',
                    }"
                  >
                    <span
                      class="mt-2 w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style="background: #465ff1"
                    ></span>
                    {{ point }}
                  </li>
                </ul>
              </div>
              <!-- Branding -->
              <div
                class="absolute bottom-4 left-5 text-xs font-bold tracking-widest"
                style="color: rgba(255, 255, 255, 0.08)"
              >
                TAGAD
              </div>
              <!-- Live engagement overlay -->
              <div
                class="absolute bottom-4 right-5 flex items-center gap-2 px-3 py-1.5 rounded-xl"
                style="
                  background: rgba(45, 60, 200, 0.45);
                  backdrop-filter: blur(8px);
                "
              >
                <span
                  class="w-1.5 h-1.5 rounded-full animate-pulse"
                  style="background: #7b92f5"
                ></span>
                <span class="text-xs font-semibold text-white"
                  >62% Engaged</span
                >
              </div>
            </div>

            </div>
            <!-- Slide nav footer -->
            <div class="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
              <span class="text-xs text-gray-400 hidden sm:block">{{ slideTopics[currentSlide - 1] }}</span>
              <div class="flex items-center gap-3 ml-auto">
                <button @click="prevSlide" :disabled="currentSlide === 1"
                  class="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors text-gray-500 disabled:opacity-30">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5"/></svg>
                </button>
                <span class="text-sm font-semibold text-navy px-1">Slide {{ currentSlide }} of {{ slideTopics.length }}</span>
                <button @click="nextSlide" :disabled="currentSlide === slideTopics.length"
                  class="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors text-gray-500 disabled:opacity-30">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5"/></svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Camera strip (toggleable) -->
            <div v-if="showCameras" class="grid grid-cols-3 gap-3 mt-5">
              <div
                v-for="cam in [
                  { n: 1, label: 'Front View' },
                  { n: 2, label: 'Left Side' },
                  { n: 3, label: 'Right Side' },
                ]"
                :key="cam.n"
                class="rounded-xl overflow-hidden flex flex-col items-center justify-center relative"
                style="
                  aspect-ratio: 16/9;
                  background: rgba(0, 0, 0, 0.4);
                  border: 1px solid rgba(255, 255, 255, 0.08);
                "
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-6 h-6 mb-1"
                  style="color: rgba(255, 255, 255, 0.2)"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="1.2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15.75 10.5l4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
                  />
                </svg>
                <p
                  class="text-xs font-medium"
                  style="color: rgba(255, 255, 255, 0.4)"
                >
                  Camera {{ cam.n }}
                </p>
                <p class="text-xs" style="color: rgba(255, 255, 255, 0.2)">
                  {{ cam.label }}
                </p>
                <div
                  class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-xs font-bold text-white"
                  style="background: rgba(70, 95, 241, 0.7)"
                >
                  CAM {{ cam.n }}
                </div>
                <span
                  class="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full animate-pulse"
                  style="background: #465ff1"
                ></span>
              </div>
            </div>
        </div>

        <!-- Engagement panel (right, toggleable) -->
        <transition name="eng-panel">
          <div v-if="showEngagement" class="w-72 flex-shrink-0 flex flex-col gap-4">

            <!-- Donut card -->
            <div class="page-card p-5">
              <h3 class="font-semibold text-sm mb-4 text-navy">Class Engagement</h3>
              <div class="flex justify-center mb-4">
                <svg width="120" height="120" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#f1f5f9" stroke-width="16"/>
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#2D3CC8" stroke-width="16" stroke-dasharray="187 115" stroke-dashoffset="0" transform="rotate(-90 60 60)"/>
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#10B981" stroke-width="16" stroke-dasharray="30 272" stroke-dashoffset="-187" transform="rotate(-90 60 60)"/>
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#F59E0B" stroke-width="16" stroke-dasharray="54 248" stroke-dashoffset="-217" transform="rotate(-90 60 60)"/>
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#F97316" stroke-width="16" stroke-dasharray="18 284" stroke-dashoffset="-271" transform="rotate(-90 60 60)"/>
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#EF476F" stroke-width="16" stroke-dasharray="12 290" stroke-dashoffset="-289" transform="rotate(-90 60 60)"/>
                  <text x="60" y="55" text-anchor="middle" font-family="Inter,sans-serif" font-size="18" font-weight="700" fill="#1E3A5F">62%</text>
                  <text x="60" y="70" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#94a3b8">Engaged</text>
                </svg>
              </div>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div v-for="item in donutLegend" :key="item.label" class="flex items-center gap-1.5">
                  <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ background: item.color }"></span>
                  <span class="text-gray-500">{{ item.label }} <strong class="text-navy">{{ item.pct }}%</strong></span>
                </div>
              </div>
            </div>

            <!-- Alerts card -->
            <div class="page-card p-5">
              <h3 class="font-semibold text-sm mb-3 text-navy">Live Alerts</h3>
              <div class="space-y-2.5">
                <div v-for="alert in alerts" :key="alert.id"
                  class="flex items-start gap-3 p-3 rounded-xl"
                  :style="alert.type === 'danger' ? 'background:rgba(239,71,111,0.06)' : 'background:rgba(255,183,3,0.08)'">
                  <span class="mt-1 w-2 h-2 rounded-full flex-shrink-0" :style="{ background: alert.type === 'danger' ? '#EF476F' : '#FFB703' }"></span>
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-semibold" :style="{ color: alert.type === 'danger' ? '#EF476F' : '#d97706' }">{{ alert.title }}</p>
                    <p class="text-xs text-gray-500 mt-0.5">{{ alert.msg }}</p>
                  </div>
                  <button @click="dismissAlert(alert.id)" class="text-gray-300 hover:text-gray-500 text-lg leading-none">&times;</button>
                </div>
                <p v-if="alerts.length === 0" class="text-xs text-gray-400 text-center py-2">No active alerts</p>
              </div>
            </div>

          </div>
        </transition>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
/* Engagement panel slide-in/out transition */
.eng-panel-enter-active,
.eng-panel-leave-active {
  transition:
    width 0.3s ease,
    opacity 0.3s ease;
  overflow: hidden;
}
.eng-panel-enter-from,
.eng-panel-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>
