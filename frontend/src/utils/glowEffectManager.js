/**
 * 全局光效管理器 - 优化版：平滑移动 + 柔和色相 + 炫酷但不影响可读性
 */

let animationFrameId = null
let hueAnimationId = null
let isEnabled = true
let currentHue = 200 // 起始色相（蓝色系）
let targetPositions = new WeakMap() // 存储目标位置
let currentPositions = new WeakMap() // 存储当前位置

// 初始化光效
export function initGlowEffects() {
  // 检查用户偏好
  const savedState = localStorage.getItem('glowEffectsEnabled')
  if (savedState !== null) {
    isEnabled = savedState === 'true'
    document.body.classList.toggle('glow-disabled', !isEnabled)
  }
  
  if (isEnabled) {
    updateHue()
    document.addEventListener('mousemove', handleGlobalMouseMove, { passive: true })
    smoothUpdate()
  }
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
  document.removeEventListener('mousemove', handleGlobalMouseMove)
}

// 切换光效（返回新状态）
export function toggle() {
  isEnabled = !isEnabled
  document.body.classList.toggle('glow-disabled', !isEnabled)
  localStorage.setItem('glowEffectsEnabled', isEnabled.toString())
  
  if (isEnabled) {
    updateHue()
    document.addEventListener('mousemove', handleGlobalMouseMove, { passive: true })
    smoothUpdate()
  } else {
    cleanupGlowEffects()
  }
  
  return isEnabled
}

// 获取当前状态
export function isGlowEnabled() {
  return isEnabled
}

// 动态色相更新 - 更慢更柔和，炫酷但不影响可读性
function updateHue() {
  if (!isEnabled) return
  
  // 色相在 180-240 之间缓慢变化（蓝青紫色系，避免红黄等刺眼颜色）
  const time = Date.now() / 4000 // 更慢的变化速度
  currentHue = 210 + Math.sin(time) * 30 // 中心色相 210（青蓝色）
  
  // 降低饱和度和亮度，确保不影响文字可读性
  const saturation = 45 // 中等饱和度
  const lightness = 60 // 中等亮度
  
  // 主光效颜色（用于按钮、卡片等）
  const glowColor = `hsla(${currentHue}, ${saturation}%, ${lightness}%, 0.6)`
  
  // 次要光效颜色（更柔和）
  const glowColorSoft = `hsla(${currentHue}, ${saturation - 10}%, ${lightness + 5}%, 0.4)`
  
  // 边框光效（非常柔和）
  const glowBorder = `hsla(${currentHue}, ${saturation}%, ${lightness + 10}%, 0.3)`
  
  document.documentElement.style.setProperty('--glow-color', glowColor)
  document.documentElement.style.setProperty('--glow-color-soft', glowColorSoft)
  document.documentElement.style.setProperty('--glow-border', glowBorder)
  
  // 为文字添加微妙的光晕（不影响可读性）
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
    
    // 平滑插值 (lerp) - 更快的响应速度
    const ease = 0.2
    current.x += (target.x - current.x) * ease
    current.y += (target.y - current.y) * ease
    
    currentPositions.set(el, current)
    el.style.setProperty('--x', `${current.x}px`)
    el.style.setProperty('--y', `${current.y}px`)
  })
  
  animationFrameId = requestAnimationFrame(smoothUpdate)
}

// 全局鼠标移动处理
function handleGlobalMouseMove(e) {
  if (!isEnabled) return
  
  const glowElements = document.querySelectorAll('.glow-btn, .glow-button, .glow-card, .glow-menu-item, .glow-input')
  
  glowElements.forEach(el => {
    const rect = el.getBoundingClientRect()
    
    // 检查鼠标是否在元素附近（扩大检测范围）
    const padding = 100 // 增大检测范围
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
