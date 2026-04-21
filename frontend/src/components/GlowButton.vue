<template>
  <button 
    ref="glowBtn" 
    :class="['glow-btn', size, type, { disabled: disabled }]"
    :disabled="disabled"
    @mousemove="handleMouseMove"
    :style="buttonStyle"
  >
    <span><slot>{{ text }}</slot></span>
  </button>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  size: { type: String, default: '' }, // small, large
  type: { type: String, default: 'primary' }, // primary, success, warning, danger
  disabled: { type: Boolean, default: false },
  colorSpeed: { type: Number, default: 50 },
  enableColorAnimation: { type: Boolean, default: true }
})

const glowBtn = ref(null)
const x = ref('50%')
const y = ref('50%')
const lightColor = ref('#00d2ff')
const animationFrameId = ref(null)

const buttonStyle = computed(() => ({
  '--x': x.value,
  '--y': y.value,
  '--light-color': lightColor.value
}))

const handleMouseMove = (e) => {
  if (!glowBtn.value || props.disabled) return
  const rect = glowBtn.value.getBoundingClientRect()
  x.value = `${e.clientX - rect.left}px`
  y.value = `${e.clientY - rect.top}px`
}

const updateHue = () => {
  if (!props.enableColorAnimation) return
  const hue = (Date.now() / props.colorSpeed) % 360
  lightColor.value = `hsl(${hue}, 100%, 70%)`
  animationFrameId.value = requestAnimationFrame(updateHue)
}

onMounted(() => {
  if (props.enableColorAnimation) updateHue()
})

onUnmounted(() => {
  if (animationFrameId.value) cancelAnimationFrame(animationFrameId.value)
})
</script>

<style scoped>
.glow-btn {
  position: relative;
  padding: 12px 24px;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  background: #1a1a2e;
  border: none;
  outline: none;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s ease;
  --light-color: #00d2ff;
  --dark-color: #333;
}

.glow-btn::before {
  content: "";
  position: absolute;
  inset: -2px;
  z-index: -1;
  border-radius: 10px;
  background: radial-gradient(
    circle at var(--x, 50%) var(--y, 50%), 
    var(--light-color) 0%, 
    var(--dark-color) 100%
  );
  opacity: 0.8;
  transition: opacity 0.3s;
}

.glow-btn:hover::before { opacity: 1; }

.glow-btn span {
  position: relative;
  z-index: 2;
  background: radial-gradient(
    circle at var(--x, 50%) var(--y, 50%), 
    var(--light-color) 0%, 
    #aaa 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.glow-btn.small { padding: 8px 16px; font-size: var(--text-base); }
.glow-btn.large { padding: 16px 32px; font-size: var(--text-xl); }

.glow-btn.success { --light-color: #00ff88; }
.glow-btn.warning { --light-color: #ffaa00; }
.glow-btn.danger { --light-color: #ff4444; }

.glow-btn.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.glow-btn.disabled::before { opacity: 0.3; }
</style>
