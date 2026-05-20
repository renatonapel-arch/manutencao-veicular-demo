import { useEffect, useState } from 'react'

const MOBILE_BP = '(max-width: 767px)'

export function useIsMobile(): boolean {
  const get = () => typeof window !== 'undefined' && window.matchMedia(MOBILE_BP).matches
  const [m, setM] = useState<boolean>(get)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia(MOBILE_BP)
    const handler = () => setM(mq.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return m
}
