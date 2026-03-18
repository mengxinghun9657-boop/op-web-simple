/**
 * 全局光效管理器 - 性能优化版
 * 默认关闭，减少性能开销
 */

let animationFrameId = null
let hueAnimationId = null
let isEnabled = false // 默认关闭光效
let currentHue = 200
let targetPositions = new WeakMap()
let currentPositions = new WeakMap()
let throttleTimer = null

// 初始化光效
export function initGlowEffects() {
  // 检查用户偏好，默认关闭
  const savedState = localStorage.getItem('glowEffectsEnabled')
  isEnabled = savedState === 'true' // 明确为 true 才开启
  document.body.classList.toggle('glow-disabled', !isEnabled)

  if (isEnabled) {
    startEffects()
  }
}

// 启动光效
function startEffects() {
  updateHue()
  document.addEventListener('mousemove', handleGlobalMouseMove, { passive: true })
  smoothUpdate()
}

// 清理光效
export function cleanupGlowEffects() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  if (hueAnimationId) {
    cancelAnimationFrame(hueAnimationId)
    hueAnimationId = null
  }
  if (throttleTimer) {
    clearTimeout(throttleTimer)
    throttleTimer = null
  }
  document.removeEventListener('mousemove', handleGlobalMouseMove)
}

// 切换光效（返回新状态）
export function toggle() {
  isEnabled = !isEnabled
  document.body.classList.toggle('glow-disabled', !isEnabled)
  localStorage.setItem('glowEffectsEnabled', isEnabled.toString())

  if (isEnabled) {
    startEffects()
  } else {
    cleanupGlowEffects()
  }

  return isEnabled
}

// 获取当前状态
export function isGlowEnabled() {
  return isEnabled
}

// 动态色相更新
function updateHue() {
  if (!isEnabled) return

  const time = Date.now() / 4000
  currentHue = 210 + Math.sin(time) * 30

  const saturation = 45
  const lightness = 60

  const glowColor = `hsla(${currentHue}, ${saturation}%, ${lightness}%, 0.6)`
  const glowColorSoft = `hsla(${currentHue}, ${saturation - 10}%, ${lightness + 5}%, 0.4)`
  const glowBorder = `hsla(${currentHue}, ${saturation}%, ${lightness + 10}%, 0.3)`

  document.documentElement.style.setProperty('--glow-color', glowColor)
  document.documentElement.style.setProperty('--glow-color-soft', glowColorSoft)
  document.documentElement.style.setProperty('--glow-border', glowBorder)

  const textGlow = `0 0 20px hsla(${currentHue}, ${saturation}%, ${lightness + 20}%, 0.15)`
  document.documentElement.style.setProperty('--text-glow', textGlow)

  hueAnimationId = requestAnimationFrame(updateHue)
}

// 平滑更新位置
function smoothUpdate() {
  if (!isEnabled) return

  const glowElements = document.querySelectorAll('.glow-btn, .glow-button, .glow-card, .glow-menu-item, .glow-input')

  glowElements.forEach(el => {
    const target = targetPositions.get(el)
    if (!target) return

    let current = currentPositions.get(el) || { x: target.x, y: target.y }

    const ease = 0.2
    current.x += (target.x - current.x) * ease
    current.y += (target.y - current.y) * ease

    currentPositions.set(el, current)
    el.style.setProperty('--x', `${current.x}px`)
    el.style.setProperty('--y', `${current.y}px`)
  })

  animationFrameId = requestAnimationFrame(smoothUpdate)
}

// 全局鼠标移动处理 - 节流优化
function handleGlobalMouseMove(e) {
  if (!isEnabled || throttleTimer) return

  throttleTimer = setTimeout(() => {
    throttleTimer = null
  }, 16) // ~60fps

  const glowElements = document.querySelectorAll('.glow-btn, .glow-button, .glow-card, .glow-menu-item, .glow-input')

  glowElements.forEach(el => {
    const rect = el.getBoundingClientRect()

    const padding = 100
    if (e.clientX >= rect.left - padding && e.clientX <= rect.right + padding &&
        e.clientY >= rect.top - padding && e.clientY <= rect.bottom + padding) {
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      targetPositions.set(el, { x, y })
    }
  })
}

export default {
  initGlowEffects,
  cleanupGlowEffects,
  toggle,
  isEnabled: isGlowEnabled
}
