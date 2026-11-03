import type { Order } from '../api/types'
import { formatDate } from '../lib/format'

const ORDER_STATUS: Record<Order['status'], string> = {
  pending: 'Beklemede',
  processing: 'Hazırlanıyor',
  shipped: 'Kargoda',
  delivered: 'Teslim edildi',
  cancelled: 'İptal edildi',
}

/** The order the ticket is about, presented as its shipping label. */
export function OrderLabel({ order }: { order: Order }) {
  const timeline: [string, string | null | undefined][] = [
    ['Sipariş verildi', order.created_at],
    ['Kargoya verildi', order.shipped_at],
    ['Teslim edildi', order.delivered_at],
  ]
  return (
    <section className="label order" aria-labelledby="order-title">
      <header className="label__head">
        <h2 id="order-title" className="label__title">
          Sipariş
        </h2>
        <span className="label__order">{order.id}</span>
      </header>
      <div className="label__body">
        <p className={`order__status order__status--${order.status}`}>{ORDER_STATUS[order.status]}</p>
        <dl className="label__facts">
          <div>
            <dt>Teslimat adresi</dt>
            <dd>{order.shipping_address}</dd>
          </div>
          <div>
            <dt>Ürünler</dt>
            <dd>
              <ul className="order__items">
                {order.items.map((item) => (
                  <li key={item.sku}>
                    {item.quantity} × {item.name}
                  </li>
                ))}
              </ul>
            </dd>
          </div>
          <div>
            <dt>Toplam</dt>
            <dd>
              {order.total_amount} {order.currency}
            </dd>
          </div>
        </dl>
        <ol className="order__timeline">
          {timeline.map(([label, date]) => (
            <li key={label} className={date ? 'is-done' : undefined}>
              <span>{label}</span>
              <span className="meta">{date ? formatDate(date) : 'Henüz değil'}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
