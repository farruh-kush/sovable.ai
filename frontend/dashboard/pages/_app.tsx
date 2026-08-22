import Head from 'next/head'
import React from 'react'
import type { AppProps } from 'next/app'
import '../styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>Solvable AI</title>
        <meta name="theme-color" content="#12233f" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="alternate icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/favicon-180.png" />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
