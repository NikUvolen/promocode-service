import {
  ArrowRight,
  CalendarDays,
  Check,
  ChevronRight,
  CircleDot,
  Gamepad2,
  Gift,
  Headphones,
  Keyboard,
  Mouse,
  MousePointer2,
  Sparkles,
  TicketCheck,
  Trophy,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { drawsApiRequest } from '../api'
import Brand from '../components/Brand'
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

const prizes = [
  { icon: Headphones, title: 'AirPods', text: 'Одна пара каждый день' },
  { icon: Gift, title: '3 000 ₽', text: 'Сертификат на покупки' },
]

function formatDrawDate(value) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    timeZone: 'Europe/Moscow',
  }).format(new Date(`${value}T12:00:00+03:00`))
}

export default function LandingPage() {
  const [activeDay, setActiveDay] = useState(0)
  const [draws, setDraws] = useState([])
  const [drawsState, setDrawsState] = useState('loading')

  useEffect(() => {
    let active = true
    drawsApiRequest()
      .then((data) => {
        if (!active) return
        setDraws(data)
        setDrawsState('ready')
      })
      .catch(() => {
        if (active) setDrawsState('error')
      })
    return () => {
      active = false
    }
  }, [])

  const activeDraw = draws[activeDay]

  return (
    <div className="landing">
      <SiteHeader />
      <main>
        <section className="hero">
          <div className="hero__content">
            <p className="hero__tag"><CircleDot size={16} /> Розыгрыш идет</p>
            <h1>GEAR DROP</h1>
            <p className="hero__lead">
              Превращай промокоды<br />в новые игровые девайсы.
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
          <div className="hero__draw" aria-label="Следующий розыгрыш">
            <span>Следующий дроп</span>
            <strong>00:00 МСК</strong>
          </div>
        </section>

        <div className="game-ticker" aria-hidden="true">
          <div className="game-ticker__track">
            {[0, 1].map((group) => (
              <div className="game-ticker__group" key={group}>
                <span>8 символов</span><Sparkles />
                <span>2 приза ежедневно</span><Gamepad2 />
                <span>1 код = 1 шанс</span><Sparkles />
              </div>
            ))}
          </div>
        </div>

        <section className="steps-section" id="how-it-works">
          <div className="steps-section__intro">
            <p className="eyebrow eyebrow--light">Как участвовать</p>
            <h2>Код. Кабинет.<br />Розыгрыш.</h2>
            <p>Все просто: регистрируй код до полуночи, а результат проверяй здесь или в личном кабинете.</p>
            <Link className="button button--light steps-section__action" to="/register">
              Начать игру
              <ArrowRight size={18} />
            </Link>
          </div>
          <ol className="steps-route">
            {steps.map(({ icon: Icon, number, title, text }) => (
              <li className="route-step" key={number}>
                <span className="route-step__icon"><Icon size={22} /></span>
                <div className="route-step__content">
                  <span className="route-step__number">Шаг {number}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
                <Check className="route-step__check" size={18} />
              </li>
            ))}
            <li className="steps-route__deadline">
              <CalendarDays size={18} />
              <span>Коды текущего дня принимаются до</span>
              <strong>00:00 МСК</strong>
            </li>
          </ol>
        </section>

        <section className="prizes-section" id="prizes">
          <div className="prizes-section__visual">
            <img src="/images/gear-drop-prizes.png" alt="Игровые девайсы и беспроводные наушники среди призов" />
            <span className="image-sticker image-sticker--yellow">Daily drop</span>
          </div>
          <div className="prizes-section__content">
            <p className="eyebrow eyebrow--dark">В призовом пуле</p>
            <h2>Забирай<br />свой апгрейд</h2>
            <p className="prizes-section__lead">Каждый день определяем двух победителей. Один человек может выиграть только один раз за всю акцию.</p>
            <div className="prize-list">
              {prizes.map(({ icon: Icon, title, text }) => (
                <div className="prize-list__item" key={title}>
                  <Icon size={24} />
                  <div><strong>{title}</strong><span>{text}</span></div>
                </div>
              ))}
            </div>
            <Link className="text-action" to="/register">Зарегистрировать код <ChevronRight size={19} /></Link>
          </div>
        </section>

        <section className="winners-section" id="winners">
          <div className="winners-section__visual" aria-hidden="true">
            <div className="winners-section__symbols">
              <Keyboard size={62} strokeWidth={1.5} />
              <Trophy size={96} strokeWidth={1.4} />
              <Mouse size={52} strokeWidth={1.5} />
            </div>
            <span>GG</span>
          </div>
          <div className="winners-section__content">
            <p className="eyebrow eyebrow--light">Таблица лидеров</p>
            <h2>Победители<br />дня</h2>
            {draws.length > 0 && <div className="draw-tabs" role="tablist" aria-label="Дни розыгрыша">
              {draws.map((draw, index) => (
                <button
                  className={activeDay === index ? 'draw-tab draw-tab--active' : 'draw-tab'}
                  key={draw.draw_date}
                  type="button"
                  role="tab"
                  aria-selected={activeDay === index}
                  onClick={() => setActiveDay(index)}
                >
                  {formatDrawDate(draw.draw_date)}
                </button>
              ))}
            </div>}
            {activeDraw && <div className="draw-date"><CalendarDays size={18} /> {formatDrawDate(activeDraw.draw_date)}</div>}
            {drawsState === 'loading' && (
              <div className="winner-empty"><Gift size={24} /><div><strong>Загружаем результаты</strong><span>Подождите несколько секунд.</span></div></div>
            )}
            {drawsState === 'error' && (
              <div className="winner-empty"><Gift size={24} /><div><strong>Не удалось загрузить результаты</strong><span>Обновите страницу немного позже.</span></div></div>
            )}
            {drawsState === 'ready' && !activeDraw && (
              <div className="winner-empty"><Gift size={24} /><div><strong>Розыгрыш еще впереди</strong><span>Результаты появятся здесь после первого розыгрыша.</span></div></div>
            )}
            {activeDraw?.winners.length === 0 && (
              <div className="winner-empty"><Gift size={24} /><div><strong>Никто не выиграл</strong><span>В этом розыгрыше победителей не было.</span></div></div>
            )}
            {activeDraw?.winners.length > 0 && (
              <ul className="winner-list">
                {activeDraw.winners.map((winner) => (
                  <li key={`${activeDraw.draw_date}-${winner.prize_code}`}>
                    <span className="winner-list__icon"><Trophy size={18} /></span>
                    <div><strong>{winner.name}</strong><span>{winner.prize_name}</span></div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <Brand light />
        <p>Промокоды, ежедневные розыгрыши<br />и честный шанс на новый девайс.</p>
        <div><span>© 2026</span><span>18+</span></div>
      </footer>
    </div>
  )
}
