import React from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

export default function FieldVisualization({ fieldData }) {
  if (!fieldData || !fieldData.electricField || !fieldData.points) return null;

  const fieldLines = [];

  fieldData.electricField.forEach((field, index) => {
    if (Array.isArray(field) && field.length === 3) {
      const magnitude = Math.sqrt(field[0] ** 2 + field[1] ** 2 + field[2] ** 2);
      if (magnitude > 0.001) {
        const start = fieldData.points[index];
        const direction = field.map(f => f / magnitude);
        const length = Math.min(magnitude * 0.1, 2);

        const end = [
          start[0] + direction[0] * length,
          start[1] + direction[1] * length,
          start[2] + direction[2] * length,
        ];

        fieldLines.push(
          <Line
            key={`field-${index}`}
            points={[new THREE.Vector3(...start), new THREE.Vector3(...end)]}
            color="#4FC3F7"
            lineWidth={Math.max(magnitude * 0.5, 0.5)}
            transparent
            opacity={0.6}
          />
        );
      }
    }
  });

  return <>{fieldLines}</>;
}
