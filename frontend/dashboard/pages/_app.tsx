import Head from 'next/head'
import React, { useEffect } from 'react'
import type { AppProps } from 'next/app'
import { useRouter } from 'next/router'
import '../styles/globals.css'
import { LocaleProvider } from '../lib/locale'
import { trackEvent } from '../lib/analytics'

function AnalyticsBridge() {
  const router = useRouter()
  useEffect(() => {
    const handleRoute = (url: string) => trackEvent('page_view', { url })
    handleRoute(router.asPath)
    router.events.on('routeChangeComplete', handleRoute)
    return () => router.events.off('routeChangeComplete', handleRoute)
  }, [router])
  return null
}

export default function App({ Component, pageProps }: AppProps) {
  return <LocaleProvider><Head><title>Solvable AI</title><meta name="theme-color" content="#12233f" /><link rel="icon" href="/favicon.svg" type="image/svg+xml" /><link rel="alternate icon" href="/favicon.ico" /><link rel="apple-touch-icon" href="/favicon-180.png" /></Head><AnalyticsBridge /><Component {...pageProps} /></LocaleProvider>
}
