import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere } from '@react-three/drei';

export default function EMSource({ source, index, onUpdate }) {
  const meshRef = useRef();

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01;
    }
  });

  const color =
    source.type === 'charge'
      ? source.strength > 0
        ? '#00BFFF'
        : '#FF4500'
      : '#32CD32';

  const size = source.type === 'charge'
    ? Math.min(Math.abs(source.strength) * 2 + 0.1, 0.5)
    : 0.3;

  return (
    <Sphere
      ref={meshRef}
      position={source.position}
      args={[size, 16, 16]}
      onClick={() => onUpdate && onUpdate(index)}
    >
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.2}
        transparent
        opacity={0.8}
      />
    </Sphere>
  );
}
