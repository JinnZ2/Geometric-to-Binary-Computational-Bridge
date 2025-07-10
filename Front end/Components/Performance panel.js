import React, { useState, useEffect } from 'react';

export default function PerformancePanel({ solver }) {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const updateMetrics = () => {
      const report = solver.performanceMetrics.getEfficiencyReport();
      setMetrics(report);
    };

    updateMetrics();
    const interval = setInterval(updateMetrics, 1000);
    return () => clearInterval(interval);
  }, [solver]);

  if (!metrics) return null;

  return (
    <div className="absolute top-4 left-4 bg-black bg-opacity-90 text-white p-4 rounded-lg font-mono text-sm max-w-xs">
      <h3 className="text-lg font-bold mb-3 text-cyan-400">Geometric Optimization Metrics</h3>

      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-green-400">Performance Gain:</span>
          <span className="text-yellow-300 font-bold">{metrics.averageSpeedup}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-blue-400">SIMD Efficiency:</span>
          <span className="text-yellow-300">{metrics.simdEfficiency}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-purple-400">Symmetry Reduction:</span>
          <span className="text-yellow-300">{metrics.symmetryReduction}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-red-400">Solutions Computed:</span>
          <span className="text-yellow-300">{metrics.solutionsComputed}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-orange-400">Total Compute Time:</span>
          <span className="text-yellow-300">{metrics.totalComputeTime}</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-600">
        <div className="text-xs text-cyan-300">
          <div>✓ Spatial decomposition active</div>
          <div>✓ SIMD optimization enabled</div>
          <div>✓ Symmetry exploitation active</div>
          <div>✓ Geometric caching enabled</div>
        </div>
      </div>
    </div>
  );
}
