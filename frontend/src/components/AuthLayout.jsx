import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

import Brand from './Brand'

export default function AuthLayout({ eyebrow, title, description, children }) {
  return (
    <div className="auth-page">
      <header className="auth-header">
        <div className="auth-header__inner">
          <Brand />
          <Link className="back-link" to="/">
            <ArrowLeft size={18} />
            На главную
          </Link>
        </div>
      </header>

      <main className="auth-main">
        <section className="auth-side" aria-hidden="true">
          <div className="auth-side__copy">
            <p className="eyebrow eyebrow--light">Промо для тех, кто играет</p>
            <p className="auth-side__title">Твой код может стать новым девайсом.</p>
          </div>
        </section>

        <section className="auth-content">
          <div className="auth-panel">
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            {description && <p className="auth-description">{description}</p>}
            {children}
          </div>
        </section>
      </main>
    </div>
  )
}
