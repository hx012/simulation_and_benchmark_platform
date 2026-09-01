export function PortalLoopDiagram() {
  return (
    <div className="portal-loop" role="img" aria-label="业务负载依次经过 Benchmark、MSKPP 仿真器和性能分析，并形成芯片性能优化闭环">
      <svg className="portal-loop-desktop" viewBox="0 0 1000 510" aria-hidden="true">
        <defs>
          <pattern id="portal-grid" width="26" height="26" patternUnits="userSpaceOnUse">
            <path d="M26 0H0V26" className="portal-loop-grid-line" />
          </pattern>
          <radialGradient id="portal-glow-blue"><stop offset="0" stopColor="#75a9ff" stopOpacity=".18" /><stop offset="1" stopColor="#75a9ff" stopOpacity="0" /></radialGradient>
          <radialGradient id="portal-glow-cyan"><stop offset="0" stopColor="#54d5df" stopOpacity=".2" /><stop offset="1" stopColor="#54d5df" stopOpacity="0" /></radialGradient>
          <radialGradient id="portal-glow-violet"><stop offset="0" stopColor="#a99dff" stopOpacity=".17" /><stop offset="1" stopColor="#a99dff" stopOpacity="0" /></radialGradient>
          <marker id="portal-main-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill="#069eae" /></marker>
          <marker id="portal-feedback-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill="#7165d9" /></marker>
          <filter id="portal-node-shadow" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="9" stdDeviation="10" floodColor="#294c70" floodOpacity=".12" /></filter>
        </defs>

        <rect className="portal-loop-frame" x="8" y="8" width="984" height="494" rx="32" />
        <rect x="8" y="8" width="984" height="494" rx="32" fill="url(#portal-grid)" opacity=".5" />
        <ellipse cx="310" cy="295" rx="225" ry="175" fill="url(#portal-glow-blue)" />
        <ellipse cx="580" cy="295" rx="225" ry="180" fill="url(#portal-glow-cyan)" />
        <ellipse cx="850" cy="295" rx="225" ry="175" fill="url(#portal-glow-violet)" />
        <path className="portal-loop-circuit" d="M34 82h76v36h48m-124 304h76v-38h38M966 74h-72v40h-50m122 308h-78v-38h-46M72 48v26h28m828-26v26h-28M72 462v-26h28m828 26v-26h-28" />

        <g className="portal-loop-main-glow"><path d="M140 295H220" /><path d="M400 295H490" /><path d="M670 295H760" /><path d="M580 156V235" /></g>
        <g className="portal-loop-main" markerEnd="url(#portal-main-arrow)"><path d="M140 295H220" /><path d="M400 295H490" /><path d="M670 295H760" /><path d="M580 156V235" /></g>
        <g className="portal-loop-feedback" markerEnd="url(#portal-feedback-arrow)"><path d="M310 235V115H525" /><path d="M850 235V115H635" /><path d="M850 355V430H310V355" /></g>

        <g className="portal-loop-label"><text x="180" y="278">负载筛选</text><text x="445" y="278">Workload</text><text x="715" y="278">运行日志</text><text x="628" y="201">芯片配置</text></g>
        <g className="portal-loop-label portal-loop-label-feedback"><text x="418" y="100">芯片性能看护</text><text x="742" y="100">需求与架构优化</text><text x="580" y="456">Benchmark 性能优化</text></g>

        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-neutral" x="40" y="254" width="100" height="82" rx="24" /><text className="portal-loop-small-title" x="90" y="289"><tspan x="90">业务</tspan><tspan x="90" dy="22">负载</tspan></text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-benchmark" x="220" y="235" width="180" height="120" rx="25" /><text className="portal-loop-core-title" x="310" y="302">Benchmark</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-simulator" x="490" y="235" width="180" height="120" rx="25" /><text className="portal-loop-core-title" x="580" y="302">MSKPP仿真器</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-analysis" x="760" y="235" width="180" height="120" rx="25" /><text className="portal-loop-core-title" x="850" y="302">性能分析</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-chip" x="525" y="80" width="110" height="76" rx="22" /><text className="portal-loop-title" x="580" y="125">Chip</text></g>
      </svg>

      <svg className="portal-loop-mobile" viewBox="0 0 360 650" aria-hidden="true">
        <defs>
          <marker id="portal-main-arrow-mobile" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill="#069eae" /></marker>
          <marker id="portal-feedback-arrow-mobile" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill="#7165d9" /></marker>
        </defs>
        <rect className="portal-loop-frame" x="6" y="6" width="348" height="638" rx="26" />
        <g className="portal-loop-main" markerEnd="url(#portal-main-arrow-mobile)"><path d="M180 82V126" /><path d="M180 216V282" /><path d="M180 372V438" /><path d="M278 256H252V327H235" /></g>
        <g className="portal-loop-feedback" markerEnd="url(#portal-feedback-arrow-mobile)"><path d="M235 171H328V256H308" /><path d="M235 483H334V292H308" /><path d="M125 483H28V171H125" /></g>
        <g className="portal-loop-label"><text x="217" y="108">负载筛选</text><text x="180" y="253">Workload</text><text x="180" y="409">运行日志</text><text x="274" y="347">芯片配置</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-neutral" x="125" y="28" width="110" height="54" rx="18" /><text className="portal-loop-small-title" x="180" y="61">业务负载</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-benchmark" x="125" y="126" width="110" height="90" rx="22" /><text className="portal-loop-core-title" x="180" y="178">Benchmark</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-chip" x="278" y="225" width="64" height="67" rx="18" /><text className="portal-loop-small-title" x="310" y="265">Chip</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-simulator" x="125" y="282" width="110" height="90" rx="22" /><text className="portal-loop-core-title portal-loop-mobile-mskpp" x="180" y="334">MSKPP仿真器</text></g>
        <g filter="url(#portal-node-shadow)"><rect className="portal-loop-core portal-loop-analysis" x="125" y="438" width="110" height="90" rx="22" /><text className="portal-loop-core-title" x="180" y="490">性能分析</text></g>
        <g className="portal-loop-mobile-feedback"><text x="310" y="174">芯片性能看护</text><text x="310" y="420">需求与架构优化</text><text x="43" y="345">Benchmark 性能优化</text></g>
      </svg>
    </div>
  );
}
