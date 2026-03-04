/**
 * 主题管理器
 * 
 * 管理深色/浅色主题切换
 * 支持系统偏好检测和本地存储持久化
 * 
 * @version 3.0.0
 */

const THEME_KEY = 'theme-preference'
const THEME_DARK = 'dark'
const THEME_LIGHT = 'light'

/**
 * 主题管理器类
 */
class ThemeManager {
  constructor() {
    this.currentTheme = THEME_DARK
    this.listeners = new Set()
    this.mediaQuery = null
    this.init()
  }

  /**
   * 初始化主题管理器
   */
  init() {
    // 获取保存的主题偏好
    const savedTheme = this.getSavedTheme()
    
    if (savedTheme) {
      this.currentTheme = savedTheme
    } else {
      // 检测系统偏好
      this.currentTheme = this.getSystemPreference()
    }
    
    // 应用主题
    this.applyTheme(this.currentTheme)
    
    // 监听系统主题变化
    this.watchSystemPreference()
  }

  /**
   * 获取保存的主题偏好
   * @returns {string|null}
   */
  getSavedTheme() {
    try {
      return localStorage.getItem(THEME_KEY)
    } catch (error) {
      console.warn('Failed to read theme preference:', error)
      return null
    }
  }

  /**
   * 保存主题偏好
   * @param {string} theme
   */
  saveTheme(theme) {
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch (error) {
      console.warn('Failed to save theme preference:', error)
    }
  }

  /**
   * 获取系统主题偏好
   * @returns {string}
   */
  getSystemPreference() {
    try {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        return THEME_LIGHT
      }
    } catch (error) {
      console.warn('Failed to detect system preference:', error)
    }
    return THEME_DARK
  }

  /**
   * 监听系统主题变化
   */
  watchSystemPreference() {
    try {
      this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      const handler = (e) => {
        // 只有在没有手动设置主题时才跟随系统
        if (!this.getSavedTheme()) {
          const newTheme = e.matches ? THEME_DARK : THEME_LIGHT
          this.applyTheme(newTheme)
        }
      }
      
      // 使用 addEventListener 替代 addListener (已废弃)
      if (this.mediaQuery.addEventListener) {
        this.mediaQuery.addEventListener('change', handler)
      } else if (this.mediaQuery.addListener) {
        this.mediaQuery.addListener(handler)
      }
    } catch (error) {
      console.warn('Failed to watch system preference:', error)
    }
  }

  /**
   * 应用主题
   * @param {string} theme
   */
  applyTheme(theme) {
    if (!this.isValidTheme(theme)) {
      console.warn(`Invalid theme: ${theme}, falling back to dark`)
      theme = THEME_DARK
    }
    
    this.currentTheme = theme
    
    // 设置 data-theme 属性
    document.documentElement.setAttribute('data-theme', theme)
    
    // 设置 color-scheme 以支持原生元素
    document.documentElement.style.colorScheme = theme
    
    // 更新 meta theme-color
    this.updateMetaThemeColor(theme)
    
    // 通知监听器
    this.notifyListeners(theme)
  }

  /**
   * 更新 meta theme-color
   * @param {string} theme
   */
  updateMetaThemeColor(theme) {
    try {
      let metaThemeColor = document.querySelector('meta[name="theme-color"]')
      
      if (!metaThemeColor) {
        metaThemeColor = document.createElement('meta')
        metaThemeColor.name = 'theme-color'
        document.head.appendChild(metaThemeColor)
      }
      
      metaThemeColor.content = theme === THEME_DARK ? '#0f172a' : '#f8fafc'
    } catch (error) {
      console.warn('Failed to update meta theme-color:', error)
    }
  }

  /**
   * 验证主题有效性
   * @param {string} theme
   * @returns {boolean}
   */
  isValidTheme(theme) {
    return [THEME_DARK, THEME_LIGHT].includes(theme)
  }

  /**
   * 切换主题
   * @returns {string} 新主题
   */
  toggle() {
    const newTheme = this.currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK
    this.setTheme(newTheme)
    return newTheme
  }

  /**
   * 设置主题
   * @param {string} theme
   */
  setTheme(theme) {
    this.applyTheme(theme)
    this.saveTheme(theme)
  }

  /**
   * 获取当前主题
   * @returns {string}
   */
  getTheme() {
    return this.currentTheme
  }

  /**
   * 是否为深色主题
   * @returns {boolean}
   */
  isDark() {
    return this.currentTheme === THEME_DARK
  }

  /**
   * 是否为浅色主题
   * @returns {boolean}
   */
  isLight() {
    return this.currentTheme === THEME_LIGHT
  }

  /**
   * 添加主题变化监听器
   * @param {Function} callback
   * @returns {Function} 取消监听函数
   */
  onChange(callback) {
    this.listeners.add(callback)
    return () => this.listeners.delete(callback)
  }

  /**
   * 通知所有监听器
   * @param {string} theme
   */
  notifyListeners(theme) {
    this.listeners.forEach(callback => {
      try {
        callback(theme)
      } catch (error) {
        console.error('Theme change listener error:', error)
      }
    })
  }

  /**
   * 重置为系统偏好
   */
  resetToSystem() {
    try {
      localStorage.removeItem(THEME_KEY)
    } catch (error) {
      console.warn('Failed to remove theme preference:', error)
    }
    
    const systemTheme = this.getSystemPreference()
    this.applyTheme(systemTheme)
  }
}

// 创建单例实例
const themeManager = new ThemeManager()

// 导出实例和常量
export { themeManager, THEME_DARK, THEME_LIGHT }
export default themeManager