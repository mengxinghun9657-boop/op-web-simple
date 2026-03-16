/**
 * 主题管理器
 *
 * 固定使用浅色主题 (Google 标准浅色风格)
 *
 * @version 4.0.0
 */

const THEME_KEY = 'theme-preference'
const THEME_DARK = 'dark'
const THEME_LIGHT = 'light'

/**
 * 主题管理器类
 */
class ThemeManager {
  constructor() {
    this.currentTheme = THEME_LIGHT // 固定为浅色主题
    this.listeners = new Set()
    this.mediaQuery = null
    this.init()
  }

  /**
   * 初始化主题管理器
   */
  init() {
    // 强制使用浅色主题
    this.currentTheme = THEME_LIGHT

    // 应用主题
    this.applyTheme(this.currentTheme)

    // 移除系统偏好监听（不再需要）
    // this.watchSystemPreference()
  }

  /**
   * 获取保存的主题偏好（已废弃）
   * @returns {string|null}
   */
  getSavedTheme() {
    // 总是返回浅色主题
    return THEME_LIGHT
  }

  /**
   * 保存主题偏好（已废弃）
   * @param {string} theme
   */
  saveTheme(theme) {
    // 不再保存主题偏好
  }

  /**
   * 获取系统主题偏好（已废弃）
   * @returns {string}
   */
  getSystemPreference() {
    // 总是返回浅色主题
    return THEME_LIGHT
  }

  /**
   * 监听系统主题变化（已废弃）
   */
  watchSystemPreference() {
    // 不再监听系统主题变化
  }

  /**
   * 应用主题（固定为浅色）
   * @param {string} theme
   */
  applyTheme(theme) {
    // 强制使用浅色主题
    theme = THEME_LIGHT
    this.currentTheme = THEME_LIGHT

    // 设置 data-theme 属性
    document.documentElement.setAttribute('data-theme', THEME_LIGHT)

    // 设置 color-scheme 以支持原生元素
    document.documentElement.style.colorScheme = 'light'

    // 更新 meta theme-color
    this.updateMetaThemeColor(THEME_LIGHT)

    // 通知监听器
    this.notifyListeners(THEME_LIGHT)
  }

  /**
   * 更新 meta theme-color（固定浅色）
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

      // 固定使用浅色主题的颜色
      metaThemeColor.content = '#ffffff'
    } catch (error) {
      console.warn('Failed to update meta theme-color:', error)
    }
  }

  /**
   * 验证主题有效性（已废弃）
   * @param {string} theme
   * @returns {boolean}
   */
  isValidTheme(theme) {
    // 只接受浅色主题
    return theme === THEME_LIGHT
  }

  /**
   * 切换主题（已禁用）
   * @returns {string} 固定返回浅色主题
   */
  toggle() {
    // 不再支持主题切换，固定浅色
    return THEME_LIGHT
  }

  /**
   * 设置主题（已禁用）
   * @param {string} theme
   */
  setTheme(theme) {
    // 固定为浅色主题，忽略参数
    this.applyTheme(THEME_LIGHT)
  }

  /**
   * 获取当前主题
   * @returns {string} 固定返回浅色主题
   */
  getTheme() {
    return THEME_LIGHT
  }

  /**
   * 是否为深色主题
   * @returns {boolean} 固定返回 false
   */
  isDark() {
    return false
  }

  /**
   * 是否为浅色主题
   * @returns {boolean} 固定返回 true
   */
  isLight() {
    return true
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
   * 重置为系统偏好（已废弃）
   */
  resetToSystem() {
    // 固定为浅色主题
    this.applyTheme(THEME_LIGHT)
  }
}

// 创建单例实例
const themeManager = new ThemeManager()

// 导出实例和常量
export { themeManager, THEME_DARK, THEME_LIGHT }
export default themeManager