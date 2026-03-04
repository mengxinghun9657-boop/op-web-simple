/**
 * Unit tests for ValidationPanel component
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-library'
import ValidationPanel from '@/components/routing/ValidationPanel.vue'


describe('ValidationPanel', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(ValidationPanel, {
      props: {
        validationResult: null
      }
    })
  })

  it('renders correctly', () => {
    expect(wrapper.exists()).toBe(true)
  })

  it('displays success message for valid regex', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: true,
        syntax_errors: [],
        conflicts: [],
        complexity_score: 5
      }
    })

    expect(wrapper.text()).toContain('验证通过')
    expect(wrapper.find('.success-message').exists()).toBe(true)
  })

  it('displays syntax errors', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: false,
        syntax_errors: [
          {
            error_message: 'Unclosed bracket',
            position: 5,
            suggestion: '检查括号是否闭合'
          }
        ],
        conflicts: [],
        complexity_score: 0
      }
    })

    expect(wrapper.text()).toContain('Unclosed bracket')
    expect(wrapper.text()).toContain('检查括号是否闭合')
  })

  it('displays conflict warnings', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: true,
        syntax_errors: [],
        conflicts: [
          {
            type: 'exact_match',
            severity: 'high',
            rule_id: 1,
            pattern: '\\d+',
            description: '与现有规则冲突'
          }
        ],
        complexity_score: 3
      }
    })

    expect(wrapper.text()).toContain('冲突')
    expect(wrapper.find('.conflict-warning').exists()).toBe(true)
  })

  it('displays complexity score', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: true,
        syntax_errors: [],
        conflicts: [],
        complexity_score: 7
      }
    })

    expect(wrapper.text()).toContain('复杂度')
    expect(wrapper.text()).toContain('7')
  })

  it('shows different severity levels for conflicts', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: true,
        syntax_errors: [],
        conflicts: [
          { severity: 'high', description: '高严重度冲突' },
          { severity: 'medium', description: '中等严重度冲突' },
          { severity: 'low', description: '低严重度冲突' }
        ],
        complexity_score: 5
      }
    })

    expect(wrapper.findAll('.conflict-high').length).toBe(1)
    expect(wrapper.findAll('.conflict-medium').length).toBe(1)
    expect(wrapper.findAll('.conflict-low').length).toBe(1)
  })

  it('expands and collapses details', async () => {
    await wrapper.setProps({
      validationResult: {
        is_valid: false,
        syntax_errors: [{ error_message: 'Error', position: 0 }],
        conflicts: [],
        complexity_score: 0
      }
    })

    const expandButton = wrapper.find('.expand-button')
    expect(expandButton.exists()).toBe(true)

    await expandButton.trigger('click')
    expect(wrapper.vm.isExpanded).toBe(true)

    await expandButton.trigger('click')
    expect(wrapper.vm.isExpanded).toBe(false)
  })

  it('handles null validation result', () => {
    expect(wrapper.text()).not.toContain('验证通过')
    expect(wrapper.text()).not.toContain('错误')
  })
})
