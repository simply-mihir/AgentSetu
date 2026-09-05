'use client'

import { useRef, Suspense, useState, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import * as THREE from 'three'

export type FeatureShape = 'search' | 'shield' | 'token' | 'ledger'

interface Props {
  shape: FeatureShape
  color?: string
  emissive?: string
  size?: number
}

/* ── 1. AI Discovery — Magnifying glass lens + orbiting dots ──────────── */

function SearchMesh({ color, emissive }: { color: string; emissive: string }) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (groupRef.current) {
      const breathe = Math.sin(state.clock.elapsedTime * 0.8) * 0.05 + 1
      groupRef.current.scale.setScalar(breathe)
    }
  })

  return (
    <Float speed={1.2} rotationIntensity={0.0} floatIntensity={0.3}>
      <group ref={groupRef}>
        <mesh>
          <torusGeometry args={[0.75, 0.1, 24, 48]} />
          <meshPhysicalMaterial
            color={color}
            emissive={emissive}
            emissiveIntensity={0.3}
            roughness={0.05}
            metalness={0.6}
            clearcoat={1}
            clearcoatRoughness={0.1}
            transparent
            opacity={0.9}
          />
        </mesh>
        <mesh>
          <circleGeometry args={[0.73, 48]} />
          <meshPhysicalMaterial
            color="#D4FFF0"
            emissive={emissive}
            emissiveIntensity={0.15}
            roughness={0}
            metalness={0.1}
            transparent
            opacity={0.3}
            side={THREE.DoubleSide}
          />
        </mesh>
        <mesh position={[0.62, -0.62, 0]} rotation={[0, 0, Math.PI / 4]}>
          <capsuleGeometry args={[0.065, 0.5, 8, 16]} />
          <meshPhysicalMaterial
            color={emissive}
            roughness={0.15}
            metalness={0.5}
            clearcoat={0.8}
          />
        </mesh>
        <group>
          {[0, 1, 2, 3, 4, 5].map((i) => {
            const angle = (i / 6) * Math.PI * 2
            const r = 1.05
            return (
              <mesh key={i} position={[Math.cos(angle) * r, Math.sin(angle) * r, 0]}>
                <sphereGeometry args={[0.05, 12, 12]} />
                <meshBasicMaterial color={color} transparent opacity={0.7 - i * 0.08} />
              </mesh>
            )
          })}
        </group>
        <mesh position={[0.2, 0.25, 0.15]} scale={0.06}>
          <sphereGeometry args={[1, 12, 12]} />
          <meshBasicMaterial color="#FFFFFF" transparent opacity={0.5} />
        </mesh>
      </group>
    </Float>
  )
}

/* ── 2. Policy Engine — Shield with checkmark ─────────────────────────── */

function ShieldMesh({ color, emissive }: { color: string; emissive: string }) {
  const ref = useRef<THREE.Group>(null)

  const shieldShape = useMemo(() => {
    const shape = new THREE.Shape()
    shape.moveTo(0, 1.1)
    shape.bezierCurveTo(0.5, 1.05, 0.8, 0.85, 0.85, 0.55)
    shape.bezierCurveTo(0.88, 0.2, 0.8, -0.2, 0.65, -0.5)
    shape.bezierCurveTo(0.45, -0.85, 0.15, -1.05, 0, -1.15)
    shape.bezierCurveTo(-0.15, -1.05, -0.45, -0.85, -0.65, -0.5)
    shape.bezierCurveTo(-0.8, -0.2, -0.88, 0.2, -0.85, 0.55)
    shape.bezierCurveTo(-0.8, 0.85, -0.5, 1.05, 0, 1.1)
    return shape
  }, [])

  const extrudeSettings = useMemo(() => ({
    depth: 0.2,
    bevelEnabled: true,
    bevelThickness: 0.05,
    bevelSize: 0.04,
    bevelSegments: 6,
  }), [])

  const checkGeometry = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.3, 0, 0.16),
      new THREE.Vector3(-0.08, -0.28, 0.16),
      new THREE.Vector3(0.35, 0.3, 0.16),
    ], false, 'catmullrom', 0)
    return new THREE.TubeGeometry(curve, 20, 0.025, 8, false)
  }, [])

  useFrame((state) => {
    if (ref.current) {
      const breathe = Math.sin(state.clock.elapsedTime * 0.7) * 0.05 + 1
      ref.current.scale.setScalar(breathe)
    }
  })

  return (
    <Float speed={1.0} rotationIntensity={0.0} floatIntensity={0.2}>
      <group ref={ref}>
        <mesh position={[0, 0, -0.1]}>
          <extrudeGeometry args={[shieldShape, extrudeSettings]} />
          <meshPhysicalMaterial
            color={color}
            emissive={emissive}
            emissiveIntensity={0.25}
            roughness={0.08}
            metalness={0.35}
            clearcoat={0.8}
            clearcoatRoughness={0.15}
            transparent
            opacity={0.88}
          />
        </mesh>
        <mesh geometry={checkGeometry}>
          <meshBasicMaterial color="#FFFFFF" transparent opacity={0.85} />
        </mesh>
        <mesh position={[0, -0.05, 0.12]} scale={0.4}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color={emissive} transparent opacity={0.12} />
        </mesh>
      </group>
    </Float>
  )
}

/* ── 3. Bounded Authorization — Token ring with lock ──────────────────── */

function TokenMesh({ color, emissive }: { color: string; emissive: string }) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (groupRef.current) {
      const breathe = Math.sin(state.clock.elapsedTime * 0.6) * 0.05 + 1
      groupRef.current.scale.setScalar(breathe)
    }
  })

  const lockBody = useMemo(() => {
    const shape = new THREE.Shape()
    const w = 0.22, h = 0.28, r = 0.04
    shape.moveTo(-w + r, -h)
    shape.lineTo(w - r, -h)
    shape.quadraticCurveTo(w, -h, w, -h + r)
    shape.lineTo(w, h - r)
    shape.quadraticCurveTo(w, h, w - r, h)
    shape.lineTo(-w + r, h)
    shape.quadraticCurveTo(-w, h, -w, h - r)
    shape.lineTo(-w, -h + r)
    shape.quadraticCurveTo(-w, -h, -w + r, -h)
    return shape
  }, [])

  return (
    <Float speed={1.3} rotationIntensity={0.0} floatIntensity={0.3}>
      <group ref={groupRef}>
        <mesh>
          <torusGeometry args={[0.9, 0.06, 16, 48]} />
          <meshPhysicalMaterial
            color={color}
            emissive={emissive}
            emissiveIntensity={0.2}
            roughness={0.05}
            metalness={0.7}
            clearcoat={1}
            transparent
            opacity={0.7}
          />
        </mesh>
        <mesh rotation={[Math.PI / 3, 0, 0]}>
          <torusGeometry args={[0.75, 0.04, 16, 48]} />
          <meshPhysicalMaterial
            color={color}
            emissive={emissive}
            emissiveIntensity={0.15}
            roughness={0.1}
            metalness={0.5}
            transparent
            opacity={0.5}
          />
        </mesh>
        <mesh position={[0, -0.1, 0]}>
          <extrudeGeometry args={[lockBody, { depth: 0.12, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 3 }]} />
          <meshPhysicalMaterial
            color={emissive}
            roughness={0.12}
            metalness={0.6}
            clearcoat={0.9}
          />
        </mesh>
        <mesh position={[0, 0.22, 0.06]}>
          <torusGeometry args={[0.13, 0.035, 12, 24, Math.PI]} />
          <meshPhysicalMaterial
            color={emissive}
            roughness={0.1}
            metalness={0.7}
            clearcoat={0.8}
          />
        </mesh>
        <mesh position={[0, -0.08, 0.14]}>
          <circleGeometry args={[0.04, 16]} />
          <meshBasicMaterial color="#FFFFFF" transparent opacity={0.6} />
        </mesh>
        {[0, 1, 2, 3].map((i) => {
          const angle = (i / 4) * Math.PI * 2 + Math.PI / 4
          return (
            <mesh key={i} position={[Math.cos(angle) * 0.9, Math.sin(angle) * 0.9, 0]} scale={0.04}>
              <sphereGeometry args={[1, 8, 8]} />
              <meshBasicMaterial color="#FFFFFF" transparent opacity={0.4} />
            </mesh>
          )
        })}
      </group>
    </Float>
  )
}

/* ── 4. Immutable Audit — Stacked ledger blocks (chain-like) ──────────── */

function LedgerMesh({ color, emissive }: { color: string; emissive: string }) {
  const ref = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (ref.current) {
      const breathe = Math.sin(state.clock.elapsedTime * 0.75) * 0.05 + 1
      ref.current.scale.setScalar(breathe)
    }
  })

  const blocks = useMemo(() => [
    { pos: [0, 0.55, 0] as [number, number, number], scale: [0.7, 0.22, 0.5] as [number, number, number], opacity: 0.95 },
    { pos: [0, 0.18, 0] as [number, number, number], scale: [0.78, 0.22, 0.55] as [number, number, number], opacity: 0.85 },
    { pos: [0, -0.19, 0] as [number, number, number], scale: [0.85, 0.22, 0.6] as [number, number, number], opacity: 0.75 },
    { pos: [0, -0.56, 0] as [number, number, number], scale: [0.92, 0.22, 0.65] as [number, number, number], opacity: 0.65 },
  ], [])

  const linkPositions = useMemo(() => [
    [0, 0.37, 0.15] as [number, number, number],
    [0, 0, 0.15] as [number, number, number],
    [0, -0.37, 0.15] as [number, number, number],
  ], [])

  return (
    <Float speed={0.9} rotationIntensity={0.0} floatIntensity={0.2}>
      <group ref={ref}>
        {blocks.map((block, i) => (
          <group key={i}>
            <mesh position={block.pos} scale={block.scale}>
              <boxGeometry args={[1, 1, 1]} />
              <meshPhysicalMaterial
                color={color}
                emissive={emissive}
                emissiveIntensity={0.2 + i * 0.05}
                roughness={0.06}
                metalness={0.3}
                clearcoat={0.9}
                clearcoatRoughness={0.1}
                transparent
                opacity={block.opacity}
              />
            </mesh>
            <mesh position={[block.pos[0], block.pos[1], block.pos[2] + block.scale[2] / 2 + 0.005]}>
              <planeGeometry args={[block.scale[0] * 0.6, 0.03]} />
              <meshBasicMaterial color="#FFFFFF" transparent opacity={0.25} side={THREE.DoubleSide} />
            </mesh>
          </group>
        ))}

        {linkPositions.map((pos, i) => (
          <mesh key={`link-${i}`} position={pos} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.06, 0.02, 8, 16]} />
            <meshPhysicalMaterial
              color={emissive}
              metalness={0.8}
              roughness={0.1}
              transparent
              opacity={0.6}
            />
          </mesh>
        ))}

        <mesh position={[0, 0.55, 0.28]} scale={0.08}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color="#FFFFFF" transparent opacity={0.35} />
        </mesh>
      </group>
    </Float>
  )
}

/* ── CSS fallback (no WebGL) ──────────────────────────────────────────── */

function CSSFallback({ color, emissive, size, shape }: { color: string; emissive: string; size: number; shape: FeatureShape }) {
  const icons: Record<FeatureShape, string> = {
    search: '🔍',
    shield: '🛡️',
    token: '🔐',
    ledger: '📋',
  }
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <div
        className="rounded-2xl flex items-center justify-center"
        style={{
          width: size * 0.65, height: size * 0.65,
          background: `
            radial-gradient(circle at 35% 30%, rgba(255,255,255,0.5), transparent 50%),
            radial-gradient(circle at 50% 50%, ${color}, ${emissive}80)
          `,
          boxShadow: `
            inset -6px -6px 16px rgba(0,0,0,0.06),
            inset 3px 3px 12px rgba(255,255,255,0.4),
            0 0 24px ${emissive}25
          `,
          fontSize: size * 0.25,
          animation: 'float 6s ease-in-out infinite',
        }}
      >
        {icons[shape]}
      </div>
    </div>
  )
}

/* ── Main export ───────────────────────────────────────────────────────── */

export default function Pillar3DObject({
  shape,
  color = '#67D8B5',
  emissive = '#168F79',
  size = 160,
}: Props) {
  const [webglFailed, setWebglFailed] = useState(false)

  if (webglFailed) {
    return <CSSFallback color={color} emissive={emissive} size={size} shape={shape} />
  }

  return (
    <div style={{ width: size, height: size }}>
      <Canvas
        camera={{ position: [0, 0, 4], fov: 34 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0)
          gl.toneMapping = THREE.ACESFilmicToneMapping
          gl.toneMappingExposure = 0.95
        }}
        onError={() => setWebglFailed(true)}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[4, 4, 5]} intensity={0.6} color="#FCFEFD" />
          <directionalLight position={[-2, -1, 3]} intensity={0.3} color="#DDF8EF" />
          <pointLight position={[2, 1, 3]} intensity={0.2} color="#74DCC0" />
          {shape === 'search' && <SearchMesh color={color} emissive={emissive} />}
          {shape === 'shield' && <ShieldMesh color={color} emissive={emissive} />}
          {shape === 'token' && <TokenMesh color={color} emissive={emissive} />}
          {shape === 'ledger' && <LedgerMesh color={color} emissive={emissive} />}
        </Suspense>
      </Canvas>
    </div>
  )
}
