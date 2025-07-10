import React, { useState, useCallback } from 'react';

export default function ControlInterface({ solver, onSourcesUpdate }) {
  const [isComputing, setIsComputing] = useState(false);
  const [selectedSourceType, setSelectedSourceType] = useState('charge');

  const addSource = useCallback((type, position) => {
    const newSource = {
      type,
      position: [...position],
      strength: type === 'charge' ? (Math.random() > 0.5 ? 1e-9 : -1e-9) : 0.1,
      id: Date.now()
    };

    if (type === 'current') {
      newSource.start = position;
      newSource.end = [position[0] + 1, position[1], position[2]];
      newSource.direction = [1, 0, 0];
    }

    solver.sources.push(newSource);
    onSourcesUpdate([...solver.sources]);
  }, [solver, onSourcesUpdate]);

  const runOptimization = useCallback(async () => {
    if (solver.sources.length === 0) return;
    setIsComputing(true);

    try {
      const bounds = { min: [-5, -5, -5], max: [5, 5, 5] };
      const fieldData = solver.calculateElectromagneticField(
        solver.sources,
        bounds,
        32
      );

      solver.fieldData = fieldData;
      onSourcesUpdate([...solver.sources]);
    } catch (error) {
      console.error('Optimization failed:', error);
    } finally {
      setIsComputing(false);
    }
  }, [solver, onSourcesUpdate]);

  const clearAll = useCallback(() => {
    solver.sources.length = 0;
    solver.fieldData = null;
    onSourcesUpdate([]);
  }, [solver, onSourcesUpdate]);

  return (
    <div className="absolute top-4 right-4 bg-black bg-opacity-90 text-white p-4 rounded-lg">
      <h3 className="text-lg font-bold mb-4 text-cyan-400">Geometric EM Solver</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Source Type</label>
          <select
            value={selectedSourceType}
            onChange={(e) => setSelectedSourceType(e.target.value)}
            className="w-full p-2 bg-gray-800 border border-gray-600 rounded"
          >
            <option value="charge">Electric Charge</option>
            <option value="current">Current Loop</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() =>
              addSource(selectedSourceType, [
                Math.random() * 4 - 2,
                Math.random() * 4 - 2,
                Math.random() * 4 - 2
              ])
            }
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
          >
            Add Source
          </button>

          <button
            onClick={runOptimization}
            disabled={isComputing}
            className={`px-3 py-2 rounded text-sm ${
              isComputing ? 'bg-gray-600' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isComputing ? 'Computing...' : 'Solve Fields'}
          </button>
        </div>

        <button
          onClick={clearAll}
          className="w-full px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm"
        >
          Clear All
        </button>

        <div className="pt-4 border-t border-gray-600">
          <div className="text-xs text-gray-400">
            Sources: {solver.sources.length}
          </div>
        </div>
      </div>
    </div>
  );
}
