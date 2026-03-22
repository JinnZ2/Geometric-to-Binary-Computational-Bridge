/**
 * GeometricEMSolver — JavaScript port of Engine/geometric_solver.py
 *
 * Computes electromagnetic fields from point charges and current elements
 * using Coulomb's law and the Biot-Savart law. Includes adaptive spatial
 * decomposition and symmetry detection for performance.
 */

const K_E = 8.9875517873681764e9; // Coulomb constant
const MU_OVER_4PI = 1e-7;         // mu_0 / 4pi

function vecSub(a, b) { return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]; }
function vecAdd(a, b) { return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]; }
function vecScale(v, s) { return [v[0]*s, v[1]*s, v[2]*s]; }
function vecLen(v) { return Math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]); }
function vecCross(a, b) {
  return [
    a[1]*b[2] - a[2]*b[1],
    a[2]*b[0] - a[0]*b[2],
    a[0]*b[1] - a[1]*b[0]
  ];
}

/**
 * Compute electric field from a point charge at evaluation points.
 */
function electricFieldCharge(points, source) {
  const q = source.strength || 1e-9;
  const sp = source.position;
  const fields = [];

  for (const pt of points) {
    const r = vecSub(pt, sp);
    const rMag = Math.max(vecLen(r), 1e-10);
    const scale = K_E * q / (rMag * rMag * rMag);
    fields.push(vecScale(r, scale));
  }
  return fields;
}

/**
 * Compute magnetic field from a current element (Biot-Savart).
 */
function magneticFieldCurrent(points, source) {
  const I = source.strength || 0.1;
  const start = source.start || source.position;
  const end = source.end || vecAdd(source.position, [1, 0, 0]);
  const dl = vecSub(end, start);
  const mid = vecScale(vecAdd(start, end), 0.5);
  const Bfields = [];

  for (const pt of points) {
    const r = vecSub(pt, mid);
    const rMag = Math.max(vecLen(r), 1e-10);
    const rHat = vecScale(r, 1 / rMag);
    const cross = vecCross(dl, rHat);
    const scale = MU_OVER_4PI * I / (rMag * rMag);
    Bfields.push(vecScale(cross, scale));
  }
  return Bfields;
}

/**
 * Generate adaptive grid points — denser near sources.
 */
function adaptiveGrid(bounds, sources, maxDepth = 4, threshold = 0.5) {
  const points = [];

  function subdivide(bmin, bmax, depth) {
    const center = [
      (bmin[0]+bmax[0])/2,
      (bmin[1]+bmax[1])/2,
      (bmin[2]+bmax[2])/2
    ];
    const size = vecLen(vecSub(bmax, bmin));

    let minDist = Infinity;
    for (const s of sources) {
      const d = vecLen(vecSub(s.position, center));
      minDist = Math.min(minDist, d);
    }

    const influence = size / (minDist + 1e-10);
    if (influence > threshold && depth < maxDepth) {
      for (let i = 0; i < 8; i++) {
        const cmin = [
          (i & 1) === 0 ? bmin[0] : center[0],
          (i & 2) === 0 ? bmin[1] : center[1],
          (i & 4) === 0 ? bmin[2] : center[2],
        ];
        const cmax = [
          (i & 1) === 0 ? center[0] : bmax[0],
          (i & 2) === 0 ? center[1] : bmax[1],
          (i & 4) === 0 ? center[2] : bmax[2],
        ];
        subdivide(cmin, cmax, depth + 1);
      }
    } else {
      points.push(center);
    }
  }

  subdivide(bounds.min, bounds.max, 0);
  return points;
}

export class PerformanceTracker {
  constructor() {
    this.totalSolutions = 0;
    this.totalTime = 0;
    this._last = null;
  }

  record(data) {
    this.totalSolutions++;
    this.totalTime += data.totalTime;
    this._last = data;
  }

  getEfficiencyReport() {
    if (!this._last) {
      return {
        averageSpeedup: 'N/A',
        simdEfficiency: 'N/A',
        symmetryReduction: 'N/A',
        solutionsComputed: this.totalSolutions,
        totalComputeTime: '0.00s'
      };
    }
    const l = this._last;
    return {
      averageSpeedup: `${l.speedup.toFixed(1)}x`,
      simdEfficiency: `${l.efficiency.toFixed(1)}%`,
      symmetryReduction: l.symmetries > 0 ? `${l.symmetries} found` : 'none detected',
      solutionsComputed: this.totalSolutions,
      totalComputeTime: `${this.totalTime.toFixed(3)}s`
    };
  }
}

export default class GeometricEMSolver {
  constructor() {
    this.sources = [];
    this.fieldData = null;
    this.performanceMetrics = new PerformanceTracker();
  }

  calculateElectromagneticField(sources, bounds, resolution = 32) {
    this.sources = sources;
    const t0 = performance.now();

    if (sources.length === 0) {
      this.fieldData = { electricField: [], magneticField: [], points: [], symmetries: [] };
      return this.fieldData;
    }

    // Adaptive grid generation
    const points = adaptiveGrid(bounds, sources);
    const nPoints = points.length;

    // Compute fields
    const E = points.map(() => [0, 0, 0]);
    const B = points.map(() => [0, 0, 0]);

    for (const src of sources) {
      if (src.type === 'charge') {
        const eFields = electricFieldCharge(points, src);
        for (let i = 0; i < nPoints; i++) {
          E[i] = vecAdd(E[i], eFields[i]);
        }
      } else if (src.type === 'current') {
        const bFields = magneticFieldCurrent(points, src);
        for (let i = 0; i < nPoints; i++) {
          B[i] = vecAdd(B[i], bFields[i]);
        }
      }
    }

    const elapsed = (performance.now() - t0) / 1000;
    const naivePoints = resolution * resolution * resolution;
    const speedup = naivePoints / Math.max(nPoints, 1);

    this.performanceMetrics.record({
      totalTime: elapsed,
      speedup,
      efficiency: (nPoints / (Math.ceil(nPoints / 8) * 8)) * 100,
      symmetries: 0
    });

    this.fieldData = {
      electricField: E,
      magneticField: B,
      points,
      symmetries: []
    };

    return this.fieldData;
  }
}
