import { LogIn, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAuth } from '../auth'
import Brand from './Brand'

export default function SiteHeader() {
  const { authenticated } = useAuth()

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Brand />
        <nav className="site-nav" aria-label="Основная навигация">
          <a className="site-nav__link" href="#how-it-works">
            Как участвовать
          </a>
          <a className="site-nav__link" href="#prizes">
            Призы
          </a>
          <a className="site-nav__link" href="#winners">
            Победители
          </a>
          {authenticated ? (
            <Link className="button button--dark button--compact" to="/account">
              <UserRound size={18} />
              <span>Кабинет</span>
            </Link>
          ) : (
            <>
              <Link className="site-nav__link site-nav__login" to="/login">
                Войти
              </Link>
              <Link className="button button--dark button--compact" to="/register">
                <LogIn size={18} />
                <span>Участвовать</span>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
