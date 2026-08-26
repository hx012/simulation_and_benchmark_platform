export function PortalLoopDiagram() {
  return (
    <div className="portal-loop" role="img" aria-label="负载、Benchmark、芯片、MSKPP 与性能分析形成的工程闭环">
      <svg viewBox="0 -32 760 360" aria-hidden="true">
        <defs>
          <marker id="loop-arrow-cyan" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#08a9b7" />
          </marker>
          <marker id="loop-arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#3168e8" />
          </marker>
          <marker id="loop-arrow-violet" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#7165d9" />
          </marker>
          <linearGradient id="mskpp-node" x1="0" x2="1">
            <stop offset="0" stopColor="#3168e8" />
            <stop offset="1" stopColor="#08a9b7" />
          </linearGradient>
        </defs>

        <g className="loop-flow loop-flow-main" markerEnd="url(#loop-arrow-cyan)">
          <path d="M 92 158 H 155" />
          <path d="M 290 158 H 405" />
          <path d="M 540 158 H 655" />
        </g>
        <g className="loop-flow loop-flow-control" markerEnd="url(#loop-arrow-blue)">
          <path d="M 223 110 V 49 H 425" />
          <path d="M 472 78 V 110" />
        </g>
        <g className="loop-flow loop-flow-feedback" markerEnd="url(#loop-arrow-violet)">
          <path d="M 697 110 V 49 H 520" />
          <path d="M 697 206 V 256 H 223 V 206" />
        </g>

        <g className="loop-labels">
          <text x="112" y="143">筛选</text>
          <text x="333" y="143">Workload</text>
          <text x="590" y="143">日志</text>
          <text x="286" y="38">芯片性能看护</text>
          <text x="548" y="38">芯片需求与架构优化</text>
          <text x="486" y="98">芯片配置</text>
          <text x="402" y="276">Benchmark 性能优化</text>
        </g>

        <g className="loop-node loop-node-load">
          <rect x="22" y="130" width="70" height="56" rx="16" />
          <text x="57" y="153">业务</text><text x="57" y="171">负载</text>
        </g>
        <g className="loop-node">
          <rect x="155" y="110" width="135" height="96" rx="18" />
          <text x="223" y="151">Benchmark</text><text className="loop-node-sub" x="223" y="174">典型负载与基线</text>
        </g>
        <g className="loop-node loop-node-mskpp">
          <rect x="405" y="110" width="135" height="96" rx="18" />
          <text x="472" y="150">MSKPP</text><text className="loop-node-sub" x="472" y="174">芯片仿真器</text>
        </g>
        <g className="loop-node loop-node-chip">
          <rect x="425" y="20" width="95" height="58" rx="16" />
          <text x="472" y="54">Chip</text>
        </g>
        <g className="loop-node">
          <rect x="655" y="110" width="85" height="96" rx="18" />
          <text x="697" y="149">性能</text><text x="697" y="172">分析</text>
        </g>
      </svg>
    </div>
  );
}
