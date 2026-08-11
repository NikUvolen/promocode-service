import { Gamepad2 } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Brand({ light = false }) {
  return (
    <Link className={`brand ${light ? 'brand--light' : ''}`} to="/">
      <span className="brand__mark" aria-hidden="true">
        <Gamepad2 size={20} strokeWidth={2.5} />
      </span>
      <span>GEAR DROP</span>
    </Link>
  )
}
