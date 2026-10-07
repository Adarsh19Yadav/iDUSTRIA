import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import NotFoundPage from '../../pages/NotFoundPage'

describe('NotFoundPage', () => {
  it('renders 404 heading', () => {
    render(<NotFoundPage />)
    expect(screen.getByText('404')).toBeInTheDocument()
    expect(screen.getByText('Page Not Found')).toBeInTheDocument()
  })
})
