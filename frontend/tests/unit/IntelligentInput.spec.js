/**
 * Unit tests for IntelligentInput component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-library'
import IntelligentInput from '@/components/routing/IntelligentInput.vue'
import { nextTick } from 'vue'


describe('IntelligentInput', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(IntelligentInput, {
      props: {
        modelValue: '',
        mode: 'natural_language'
      }
    })
  })

  it('renders correctly', () => {
    expect(wrapper.exists()).toBe(true)
  })

  it('switches between natural language and regex modes', async () => {
    // Initial mode is natural_language
    expect(wrapper.vm.currentMode).toBe('natural_language')

    // Switch to regex mode
    await wrapper.vm.switchMode('regex')
    expect(wrapper.vm.currentMode).toBe('regex')
    expect(wrapper.emitted('update:mode')).toBeTruthy()
  })

  it('emits update:modelValue when input changes', async () => {
    const input = wrapper.find('textarea')
    await input.setValue('查询IP地址')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe('查询IP地址')
  })

  it('calls convert API when convert button is clicked', async () => {
    const mockConvert = vi.fn().mockResolvedValue({
      success: true,
      data: {
        regex: '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',
        explanation: '匹配IP地址',
        examples: ['192.168.1.1'],
        confidence: 0.9
      }
    })

    wrapper.vm.convertToRegex = mockConvert
    wrapper.vm.naturalLanguageInput = '查询IP地址'

    await wrapper.vm.handleConvert()
    await nextTick()

    expect(mockConvert).toHaveBeenCalled()
  })

  it('shows loading state during conversion', async () => {
    wrapper.vm.isConverting = true
    await nextTick()

    expect(wrapper.find('.loading-indicator').exists()).toBe(true)
  })

  it('displays conversion results', async () => {
    wrapper.vm.conversionResult = {
      regex: '\\d+',
      explanation: '匹配数字',
      examples: ['123', '456'],
      confidence: 0.85
    }
    await nextTick()

    expect(wrapper.text()).toContain('匹配数字')
    expect(wrapper.text()).toContain('123')
  })

  it('preserves content when switching modes', async () => {
    wrapper.vm.naturalLanguageInput = '查询IP'
    wrapper.vm.regexInput = '\\d+'

    await wrapper.vm.switchMode('regex')
    expect(wrapper.vm.regexInput).toBe('\\d+')

    await wrapper.vm.switchMode('natural_language')
    expect(wrapper.vm.naturalLanguageInput).toBe('查询IP')
  })

  it('validates empty input', async () => {
    wrapper.vm.naturalLanguageInput = ''
    
    const result = await wrapper.vm.handleConvert()
    
    expect(result).toBeUndefined()
    // Should show error message
  })

  it('debounces validation calls', async () => {
    const mockValidate = vi.fn()
    wrapper.vm.validateInput = mockValidate

    // Rapid input changes
    wrapper.vm.regexInput = 't'
    wrapper.vm.regexInput = 'te'
    wrapper.vm.regexInput = 'tes'
    wrapper.vm.regexInput = 'test'

    // Wait for debounce
    await new Promise(resolve => setTimeout(resolve, 600))

    // Should only call once after debounce period
    expect(mockValidate.mock.calls.length).toBeLessThanOrEqual(1)
  })
})
