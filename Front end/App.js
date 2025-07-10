import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, GridHelper } from '@react-three/drei';
import EMSource from './components/EMSource';
import FieldVisualization from './components/FieldVisualization';
import PerformancePanel from './components/PerformancePanel';
import ControlInterface from './components/ControlInterface';
import GeometricEMSolver from '../engine/geometric_solver';

export default function App() {
  const [solver] = React.useState(() => new GeometricEMSolver());
  const [sources, setSources] = React.useState([]);
  const [fieldData, setFieldData] = React.useState(null);

  const handleSourcesUpdate = (newSources) => {
    setSources(newSources);
    if (solver.fieldData) {
      setFieldData(solver.fieldData);
    }
  };

  return (
    <div className="w-full h-screen relative bg-black">
      <Canvas camera={{ position: [8, 6, 8], fov: 75 }}>
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />
        <pointLight position={[-10, -10, -10]} intensity={0.4} />

        {/* Title */}
        <Text position={[0, 6, 0]} fontSize={0.8} color="#4FC3F7" anchorX="center" anchorY="middle">
          Geometric-Optimized EM Solver
        </Text>
        <Text position={[0, 5, 0]} fontSize={0.4} color="#FFFFFF" anchorX="center" anchorY="middle">
          Demonstrating 100x+ Performance Through Geometric Intelligence
        </Text>

        {/* Sources */}
        {sources.map((source, index) => (
          <EMSource key={source.id || index} source={source} index={index} />
        ))}

        {/* Fields */}
        <FieldVisualization fieldData={fieldData} />

        <GridHelper args={[20, 20]} />
        <OrbitControls enablePan enableZoom enableRotate />
      </Canvas>

      <PerformancePanel solver={solver} />
      <ControlInterface solver={solver} onSourcesUpdate={handleSourcesUpdate} />
    </div>
  );
}
