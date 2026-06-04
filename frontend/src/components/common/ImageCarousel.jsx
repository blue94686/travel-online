import { useState, useEffect, useCallback } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import './ImageCarousel.css'

export default function ImageCarousel({ images = [], alt = '', autoAdvanceMs = 0 }) {
  const [current, setCurrent] = useState(0)
  const safeImages = images.length > 0 ? images : []

  const goNext = useCallback(() => {
    setCurrent(c => (c + 1) % safeImages.length)
  }, [safeImages.length])

  const goPrev = useCallback(() => {
    setCurrent(c => (c - 1 + safeImages.length) % safeImages.length)
  }, [safeImages.length])

  useEffect(() => {
    if (!autoAdvanceMs || safeImages.length <= 1) return
    const timer = setInterval(goNext, autoAdvanceMs)
    return () => clearInterval(timer)
  }, [autoAdvanceMs, goNext, safeImages.length])

  if (safeImages.length === 0) return null
  if (safeImages.length === 1) return <div className="carousel-single"><img src={safeImages[0]} alt={alt} /></div>

  return (
    <div className="image-carousel">
      <div className="carousel-viewport">
        {safeImages.map((src, i) => (
          <div className={`carousel-slide ${i === current ? 'active' : ''}`} key={`${src}-${i}`}>
            <img src={src} alt={`${alt} ${i + 1}`} loading={i === 0 ? 'eager' : 'lazy'} />
          </div>
        ))}
      </div>
      <button className="carousel-btn prev" onClick={goPrev}><ChevronLeft size={24} /></button>
      <button className="carousel-btn next" onClick={goNext}><ChevronRight size={24} /></button>
      <div className="carousel-dots">
        {safeImages.map((_, i) => (
          <button className={`dot ${i === current ? 'active' : ''}`} onClick={() => setCurrent(i)} key={i} />
        ))}
      </div>
    </div>
  )
}
