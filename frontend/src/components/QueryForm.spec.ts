import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import QueryForm from './QueryForm.vue'

describe('QueryForm', () => {
  it('emits "query" with the form values when submitted', async () => {
    const wrapper = mount(QueryForm)

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.emitted('query')).toBeTruthy()
    const emittedParams = wrapper.emitted('query')![0][0] as { estacion: string; fields: string[] }
    expect(emittedParams.estacion).toBe('89070')
    expect(emittedParams.fields).toEqual([])
  })

  it('includes a field in the emitted params when its checkbox is checked', async () => {
    const wrapper = mount(QueryForm)

    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('form').trigger('submit.prevent')

    const emittedParams = wrapper.emitted('query')![0][0] as { fields: string[] }
    expect(emittedParams.fields).toContain('temperature')
  })
})