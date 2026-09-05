'use client'

import { useRef, useMemo, Suspense, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { MeshDistortMaterial, Float, Environment } from '@react-three/drei'
import * as THREE from 'three'

/* ═══════════════════════════════════════════════════════════════════════════
   AgentSetu Orb — the AI presence
   ═══════════════════════════════════════════════════════════════════════════
   A glass sphere with internal luminous green energy. Smooth, glossy, organic.
   ═══════════════════════════════════════════════════════════════════════════ */

export type OrbStatus = 'idle' | 'thinking' | 'processing' | 'success' | 'error' | 'payment' | 'approval'
export type OrbVariant = 'hero' | 'compact' | 'sidebar' | 'auth'

interface OrbProps {
  status?: OrbStatus
  variant?: OrbVariant
  className?: string
  interactive?: boolean
}

/* ── Color configs per status ─────────────────────────────────────────── */

const STATUS_CONFIGS: Record<OrbStatus, {
  color: string
  emissive: string
  emissiveIntensity: number
  distort: number
  speed: number
  innerColor: string
  innerOpacity: number
}> = {
  idle: {
    color: '#A5EBD3',
    emissive: '#2EAF91',
    emissiveIntensity: 0.3,
    distort: 0.15,
    speed: 1.2,
    innerColor: '#67D8B5',
    innerOpacity: 0.28,
  },
  thinking: {
    color: '#67D8B5',
    emissive: '#168F79',
    emissiveIntensity: 0.5,
    distort: 0.22,
    speed: 2.5,
    innerColor: '#2EAF91',
    innerOpacity: 0.38,
  },
  processing: {
    color: '#5FE9C8',
    emissive: '#14B898',
    emissiveIntensity: 0.4,
    distort: 0.18,
    speed: 2.0,
    innerColor: '#2EAF91',
    innerOpacity: 0.32,
  },
  success: {
    color: '#A5EBD3',
    emissive: '#2DAA7B',
    emissiveIntensity: 0.45,
    distort: 0.10,
    speed: 0.8,
    innerColor: '#67D8B5',
    innerOpacity: 0.30,
  },
  error: {
    color: '#F5C6CB',
    emissive: '#D97D87',
    emissiveIntensity: 0.35,
    distort: 0.25,
    speed: 3.0,
    innerColor: '#E8A0A8',
    innerOpacity: 0.30,
  },
  payment: {
    color: '#99F6E0',
    emissive: '#0D9479',
    emissiveIntensity: 0.5,
    distort: 0.08,
    speed: 1.0,
    innerColor: '#2DD4AB',
    innerOpacity: 0.35,
  },
  approval: {
    color: '#CCFBEF',
    emissive: '#168F79',
    emissiveIntensity: 0.45,
    distort: 0.12,
    speed: 1.5,
    innerColor: '#67D8B5',
    innerOpacity: 0.32,
  },
}

const VARIANT_SIZES: Record<OrbVariant, number> = {
  hero: 1.6,
  compact: 1.3,
  sidebar: 0.8,
  auth: 1.4,
}

/* ── Glass Orb — main 3D sphere ──────────────────────────────────────── */

function GlassOrb({ status, variant, interactive }: { status: OrbStatus; variant: OrbVariant; interactive: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const innerRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)
  const { pointer } = useThree()

  const config = STATUS_CONFIGS[status]
  const size = VARIANT_SIZES[variant]

  const targetRef = useRef(config)
  const currentRef = useRef({ ...config })

  useEffect(() => {
    targetRef.current = STATUS_CONFIGS[status]
  }, [status])

  useFrame((state, delta) => {
    const t = targetRef.current
    const c = currentRef.current
    const lerpSpeed = delta * 2.5

    c.emissiveIntensity += (t.emissiveIntensity - c.emissiveIntensity) * lerpSpeed
    c.distort += (t.distort - c.distort) * lerpSpeed
    c.speed += (t.speed - c.speed) * lerpSpeed
    c.innerOpacity += (t.innerOpacity - c.innerOpacity) * lerpSpeed

    if (meshRef.current) {
      // Very slow tiny rotational movement (20-60 seconds per cycle)
      meshRef.current.rotation.y += delta * 0.015 * c.speed
      meshRef.current.rotation.x += delta * 0.008

      if (interactive) {
        // Barely noticeable, elegant parallax
        const targetX = pointer.y * 0.03
        const targetZ = pointer.x * 0.03
        meshRef.current.rotation.x += (targetX - meshRef.current.rotation.x) * 0.015
        meshRef.current.rotation.z += (targetZ - meshRef.current.rotation.z) * 0.015
      }
    }

    if (innerRef.current) {
      // Slow internal light movement
      innerRef.current.rotation.y -= delta * 0.04
      innerRef.current.rotation.x += delta * 0.02
      // Subtle breathing scale (6-12 seconds)
      const breathe = Math.sin(state.clock.elapsedTime * 0.6) * 0.03 + 1
      innerRef.current.scale.setScalar(size * 0.38 * breathe)
    }

    if (glowRef.current) {
      const pulse = Math.sin(state.clock.elapsedTime * 1.2) * 0.05 + 1
      glowRef.current.scale.setScalar(size * 1.08 * pulse)
    }
  })

  const glowColor = useMemo(() => new THREE.Color(config.emissive), [config.emissive])

  return (
    <group>
      {/* Outer glow */}
      <mesh ref={glowRef} scale={size * 1.08}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color={glowColor}
          transparent
          opacity={0.03}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Main glass sphere */}
      <Float
        speed={0.8}
        rotationIntensity={0.05}
        floatIntensity={variant === 'hero' ? 0.3 : 0.15}
        floatingRange={variant === 'hero' ? [-0.05, 0.05] : [-0.02, 0.02]}
      >
        <mesh ref={meshRef} scale={size}>
          <sphereGeometry args={[1, 128, 128]} />
          <MeshDistortMaterial
            color={config.color}
            emissive={config.emissive}
            emissiveIntensity={config.emissiveIntensity * 0.8}
            roughness={0.04}
            metalness={0.1}
            clearcoat={1.0}
            clearcoatRoughness={0.05}
            distort={config.distort * 0.8}
            speed={config.speed * 0.5}
            transparent
            opacity={0.85}
            envMapIntensity={0.8}
          />
        </mesh>

        {/* Inner luminous core */}
        <mesh ref={innerRef} scale={size * 0.38}>
          <sphereGeometry args={[1, 64, 64]} />
          <meshBasicMaterial
            color={config.innerColor}
            transparent
            opacity={config.innerOpacity}
          />
        </mesh>

        {/* Specular highlight */}
        <mesh position={[size * 0.25, size * 0.3, size * 0.6]} scale={size * 0.15}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial
            color="#FFFFFF"
            transparent
            opacity={0.08}
          />
        </mesh>
      </Float>
    </group>
  )
}

/* ── CSS Fallback Orb ────────────────────────────────────────────────── */

function CSSFallbackOrb({ status, variant }: { status: OrbStatus; variant: OrbVariant }) {
  const config = STATUS_CONFIGS[status]
  const sizes: Record<OrbVariant, number> = { hero: 200, compact: 130, sidebar: 80, auth: 170 }
  const s = sizes[variant]

  return (
    <div className="relative" style={{ width: s, height: s }}>
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${config.emissive}25, transparent 70%)`,
          transform: 'scale(1.5)',
          animation: 'glow-pulse 3s ease-in-out infinite',
        }}
      />
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `
            radial-gradient(circle at 35% 30%, rgba(255,255,255,0.55), transparent 50%),
            radial-gradient(circle at 50% 50%, ${config.color}, ${config.emissive}80)
          `,
          boxShadow: `
            inset -15px -15px 35px rgba(0,0,0,0.06),
            inset 8px 8px 25px rgba(255,255,255,0.45),
            0 0 50px ${config.emissive}30,
            0 8px 32px rgba(0,0,0,0.08)
          `,
          animation: 'float 6s ease-in-out infinite',
        }}
      />
      <div
        className="absolute rounded-full"
        style={{
          top: '15%', left: '20%',
          width: '30%', height: '22%',
          background: 'radial-gradient(ellipse, rgba(255,255,255,0.55), transparent)',
          filter: 'blur(4px)',
        }}
      />
    </div>
  )
}

/* ── Main exported component ──────────────────────────────────────────── */

export default function AgentSetuOrb({
  status = 'idle',
  variant = 'hero',
  className = '',
  interactive = true,
}: OrbProps) {
  const [webglFailed, setWebglFailed] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const sizes: Record<OrbVariant, { w: number; h: number }> = {
    hero: { w: 280, h: 280 },
    compact: { w: 160, h: 160 },
    sidebar: { w: 100, h: 100 },
    auth: { w: 240, h: 240 },
  }

  const { w, h } = sizes[variant]

  if (webglFailed) {
    return (
      <div
        ref={containerRef}
        className={`flex items-center justify-center ${className}`}
        style={{ width: w, height: h }}
      >
        <CSSFallbackOrb status={status} variant={variant} />
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: w, height: h }}
    >
      <Canvas
        camera={{ position: [0, 0, 5.5], fov: 40 }}
        gl={{ antialias: true, alpha: true }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0)
          gl.toneMapping = THREE.ACESFilmicToneMapping
          gl.toneMappingExposure = 0.95
        }}
        onError={() => setWebglFailed(true)}
      >
        <Suspense fallback={null}>
          {/* Lighting + subtle environment for glass reflections */}
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.5} color="#FCFEFD" />
          <directionalLight position={[-3, -2, 4]} intensity={0.4} color="#DDF8EF" />
          <pointLight position={[3, 2, 4]} intensity={0.2} color="#74DCC0" />
          <pointLight position={[-2, -1, 3]} intensity={0.15} color="#B4ECDD" />
          <Environment preset="city" />
          <GlassOrb status={status} variant={variant} interactive={interactive} />
        </Suspense>
      </Canvas>
    </div>
  )
}
