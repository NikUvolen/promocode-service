import {
  ArrowRight,
  CalendarDays,
  Check,
  Gamepad2,
  Gift,
  Keyboard,
  MousePointer2,
  TicketCheck,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import SiteHeader from '../components/SiteHeader'

const steps = [
  {
    icon: TicketCheck,
    number: '01',
    title: 'Найди промокод',
    text: 'Внутри упаковки участвующего товара.',
  },
  {
    icon: MousePointer2,
    number: '02',
    title: 'Зарегистрируй',
    text: 'Введи код из 8 символов в личном кабинете.',
  },
  {
    icon: Gift,
    number: '03',
    title: 'Следи за розыгрышем',
    text: 'Новые победители появляются каждый день.',
  },
]

export default function LandingPage() {
  return (
    <div className="landing">
      <SiteHeader />
      <main>
        <section className="hero">
          <div className="hero__content">
            <p className="hero__tag"><Gamepad2 size={18} /> Игровая промоакция</p>
            <h1>GEAR DROP</h1>
            <p className="hero__lead">
              Регистрируй промокоды и выигрывай игровые девайсы каждый день.
            </p>
            <div className="hero__actions">
              <Link className="button button--light" to="/register">
                Участвовать
                <ArrowRight size={19} />
              </Link>
              <a className="button button--ghost-light" href="#how-it-works">
                Как это работает
              </a>
            </div>
            <p className="hero__note"><Check size={17} /> Один аккаунт, все коды и результаты</p>
          </div>
        </section>

        <section className="steps-section" id="how-it-works">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Три простых шага</p>
              <h2>От кода до приза</h2>
            </div>
            <p>Каждый зарегистрированный код участвует в ближайшем розыгрыше.</p>
          </div>
          <div className="steps-grid">
            {steps.map(({ icon: Icon, number, title, text }) => (
              <article className="step" key={number}>
                <span className="step__icon"><Icon size={24} /></span>
                <span className="step__number">{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="winners-section" id="winners">
          <div className="winners-section__visual" aria-hidden="true">
            <Keyboard size={62} strokeWidth={1.5} />
            <Gamepad2 size={88} strokeWidth={1.5} />
          </div>
          <div className="winners-section__content">
            <p className="eyebrow eyebrow--light">Результаты</p>
            <h2>Победители дня</h2>
            <div className="draw-date"><CalendarDays size={18} /> 11 августа</div>
            <div className="winner-empty">
              <Gift size={24} />
              <div>
                <strong>Розыгрыш еще впереди</strong>
                <span>Результаты появятся здесь после 00:00 по Москве.</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <span>© 2026 GEAR DROP</span>
        <span>18+</span>
      </footer>
    </div>
  )
}
