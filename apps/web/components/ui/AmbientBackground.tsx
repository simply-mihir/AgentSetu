'use client'

/**
 * Soft gradient background blobs — gives pages the characteristic
 * sea-green/mint ambient glow without being visually busy.
 */

interface Props {
  variant?: 'default' | 'auth' | 'hero' | 'subtle'
}

const configs = {
  default: [
    { className: 'ambient-blob ambient-blob-green', style: { top: '-10%', left: '15%', width: 500, height: 500, opacity: 0.20 } },
    { className: 'ambient-blob ambient-blob-mint', style: { bottom: '-5%', right: '10%', width: 400, height: 400, opacity: 0.15 } },
    { className: 'ambient-blob ambient-blob-aqua', style: { top: '40%', right: '30%', width: 300, height: 300, opacity: 0.10 } },
  ],
  auth: [
    { className: 'ambient-blob ambient-blob-green', style: { top: '-15%', left: '5%', width: 600, height: 600, opacity: 0.25 } },
    { className: 'ambient-blob ambient-blob-mint', style: { bottom: '-10%', right: '5%', width: 500, height: 500, opacity: 0.20 } },
  ],
  hero: [
    { className: 'ambient-blob ambient-blob-green', style: { top: '-20%', left: '20%', width: 700, height: 700, opacity: 0.22 } },
    { className: 'ambient-blob ambient-blob-mint', style: { bottom: '-15%', right: '15%', width: 600, height: 600, opacity: 0.18 } },
    { className: 'ambient-blob ambient-blob-aqua', style: { top: '30%', left: '50%', width: 400, height: 400, opacity: 0.12 } },
  ],
  subtle: [
    { className: 'ambient-blob ambient-blob-green', style: { top: '-5%', right: '20%', width: 350, height: 350, opacity: 0.12 } },
    { className: 'ambient-blob ambient-blob-mint', style: { bottom: '5%', left: '10%', width: 300, height: 300, opacity: 0.10 } },
  ],
}

export default function AmbientBackground({ variant = 'default' }: Props) {
  return (
    <div className="ambient-bg" aria-hidden="true">
      {configs[variant].map((blob, i) => (
        <div key={i} className={blob.className} style={blob.style} />
      ))}
    </div>
  )
}
