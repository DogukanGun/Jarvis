export default function Logo({
  size = 32,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <polygon
        points="32,5 55,18.5 55,45.5 32,59 9,45.5 9,18.5"
        stroke="#4ade80"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <polygon
        points="32,16 46,24 46,40 32,48 18,40 18,24"
        stroke="#4ade80"
        strokeWidth="0.75"
        strokeLinejoin="round"
        opacity="0.3"
      />
      <line x1="24" y1="22" x2="40" y2="22" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" />
      <path
        d="M 37 22 L 37 43 Q 37 50 26 48"
        stroke="#4ade80"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
