interface ArchitectureBackgroundProps {
  variant?: 'welcome' | 'login';
}

export function ArchitectureBackground({ variant = 'welcome' }: ArchitectureBackgroundProps) {
  const gridId = `architecture-grid-${variant}`;
  const className = variant === 'login'
    ? 'architecture-background architecture-background-login'
    : 'architecture-background architecture-background-welcome';

  return (
    <svg
      className={className}
      viewBox="0 0 1600 900"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <pattern id={gridId} width="64" height="64" patternUnits="userSpaceOnUse">
          <path d="M64 0H0V64" className="architecture-grid-line" />
        </pattern>
      </defs>

      <rect width="1600" height="900" fill={`url(#${gridId})`} />

      <g className="architecture-frame-lines">
        <path d="M0 162 H330 V96 H512" />
        <path d="M1600 182 H1348 V118 H1166" />
        <path d="M0 744 H250 V812 H468" />
        <path d="M1600 706 H1376 V792 H1188" />
        <path d="M112 322 H396 V286 H516" />
        <path d="M1488 390 H1244 V354 H1130" />
      </g>

      <g className="architecture-blocks">
        <rect x="58" y="88" width="142" height="74" rx="10" />
        <rect x="224" y="88" width="94" height="74" rx="10" />
        <rect x="88" y="196" width="230" height="104" rx="12" />

        <rect x="1280" y="86" width="118" height="82" rx="10" />
        <rect x="1422" y="86" width="116" height="82" rx="10" />
        <rect x="1280" y="202" width="258" height="94" rx="12" />

        <rect x="68" y="650" width="122" height="82" rx="10" />
        <rect x="214" y="650" width="102" height="82" rx="10" />
        <rect x="88" y="764" width="228" height="64" rx="10" />

        <rect x="1296" y="630" width="230" height="100" rx="12" />
        <rect x="1296" y="756" width="106" height="66" rx="10" />
        <rect x="1426" y="756" width="100" height="66" rx="10" />
      </g>

      <g className="architecture-block-details">
        <path d="M78 112 H176 M78 132 H154" />
        <path d="M244 112 H298 M244 132 H286" />
        <path d="M108 222 H278 M108 246 H236 M108 270 H294" />
        <path d="M1300 112 H1374 M1300 136 H1352" />
        <path d="M1442 112 H1516 M1442 136 H1490" />
        <path d="M1300 228 H1512 M1300 254 H1468" />
        <path d="M88 678 H170 M234 678 H294" />
        <path d="M108 792 H290" />
        <path d="M1318 656 H1498 M1318 684 H1456" />
        <path d="M1316 782 H1380 M1446 782 H1506" />
      </g>

      <g className="architecture-traces">
        <path d="M392 716 H514 V688 H626 V730 H756" />
        <path d="M844 148 H932 V118 H1038 V168 H1160" />
        <path d="M382 184 H470 V214 H566" />
        <path d="M1034 684 H1110 V652 H1212" />
      </g>

      <g className="architecture-events">
        <rect x="446" y="704" width="46" height="10" rx="3" />
        <rect x="528" y="684" width="64" height="10" rx="3" />
        <rect x="646" y="726" width="78" height="10" rx="3" />
        <rect x="872" y="144" width="42" height="10" rx="3" />
        <rect x="948" y="114" width="70" height="10" rx="3" />
        <rect x="1056" y="164" width="82" height="10" rx="3" />
      </g>
    </svg>
  );
}
