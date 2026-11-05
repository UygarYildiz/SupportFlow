import { type CSSProperties, useEffect } from 'react'
import { Link } from 'react-router'
import { wakeBackend } from '../api/client'

// Public product page of the live demo (src/app/landing.ts decides when it is shown).
// Copy follows what the product does today; planned work is labelled as planned.
const REPO_URL = 'https://github.com/UygarYildiz/SupportFlow'
const SELF_HOSTING_URL = `${REPO_URL}/blob/main/docs/SELF_HOSTING.md`
const ROADMAP_URL = `${REPO_URL}/blob/main/ROADMAP.md`

const STEPS = [
  {
    title: 'Müşteri yazar',
    text: 'Destek adresinize gelen e-postalar kendiliğinden talebe dönüşür. Talepleri panelden de açabilirsiniz.',
  },
  {
    title: 'Yapay zekâ hazırlar',
    text: 'Siparişe ve mağaza kurallarınıza bakar, bir yanıt taslağı yazar. Gerekirse adres değişikliği ya da iade gibi bir işlem önerir.',
  },
  {
    title: 'Siz karar verirsiniz',
    text: 'Taslağı okur, düzeltir ve gönderirsiniz. Önerilen işlem ancak sizin onayınızla ve yalnızca bir kez uygulanır.',
  },
]

const GUARANTEES = [
  {
    title: 'Kendi başına hiçbir şey yapmaz',
    text: 'Yapay zekâ e-posta göndermez, siparişe dokunmaz. Yalnızca öneri hazırlar; dışarıya giden her şey bir çalışanın kararından geçer.',
  },
  {
    title: 'Uydurmaz, kaynağını gösterir',
    text: 'Bulamadığı siparişi var saymaz, eksik bilgiyi müşteriden ister. Dayandığı kuralı madde numarasıyla gösterir.',
  },
  {
    title: 'Bir onay, tek işlem',
    text: 'Çift tıklama ya da iki kişinin aynı anda onaylaması iki iade yapmaz. Onay anında siparişin güncel durumu yeniden kontrol edilir.',
  },
  {
    title: 'Her karar kayıt altında',
    text: 'Kim neyi, ne zaman ve hangi gerekçeyle onayladı ya da reddetti, değiştirilemeyen bir denetim kaydında durur.',
  },
]

const FEATURES = [
  { title: 'E-posta kanalı', text: 'Posta kutunuzu bağlayın; gelen iletiler talep olur, yanıtlar aynı yazışmanın içinden gider.' },
  { title: 'Kurallara dayalı yanıtlar', text: 'İade, teslimat ve adres değişikliği politikalarınız taslakların dayanağıdır.' },
  { title: 'Rollere göre yetki', text: 'Destek uzmanı adres değişikliğini onaylar; iadeyi yalnız yönetici onaylar.' },
  { title: 'Onay kuyruğu', text: 'Bekleyen bütün öneriler tek ekranda; süresi dolan öneri asla kendiliğinden uygulanmaz.' },
  { title: 'Ekip yönetimi', text: 'Çalışma arkadaşlarınızı ekleyin, rollerini belirleyin, ayrılanı pasifleştirin.' },
  { title: 'Türkçe', text: 'Arayüz, hata mesajları ve yapay zekânın yazdığı taslaklar Türkçe.' },
]

const NEXT_UP = [
  'CSV ile müşteri ve sipariş yükleme',
  'İşletmenize özgü kurallar ve politikalar',
  'Kendi model anahtarınız ya da yerel model (Ollama)',
  'Web formu ve webhook',
  'Shopify, WooCommerce ve İkas bağlantıları',
  'WhatsApp Business',
]

const FAQ = [
  {
    q: 'Ücretli mi?',
    a: 'Hayır. Kaynak kodu GitHub’da açık; kendi sunucunuza ücretsiz kurarsınız. Gerçek yapay zekâ modelini açarsanız modelin kullanım ücreti, kendi anahtarınızla doğrudan sağlayıcıya ödenir.',
  },
  {
    q: 'Müşteri verilerim nerede durur?',
    a: 'Kendi kurulumunuzda, kendi makinenizdeki veritabanında. Her kurulum tek bir işletmeye hizmet eder; verileriniz başka bir işletmeyle aynı yerde tutulmaz. Gerçek modeli açarsanız incelenen talep ve ilgili sipariş bilgisi model sağlayıcısına gönderilir; kapalıyken modele hiçbir veri gönderilmez.',
  },
  {
    q: 'Yapay zekâ yanlış bir şey önerirse?',
    a: 'Öneriyi reddedersiniz ve hiçbir şey olmaz. Taslak düzenlenebilir bir metindir; mağaza kurallarına uymayan bir işlem önerisi ise onaylanamaz bile.',
  },
  {
    q: 'Demodaki veriler gerçek mi?',
    a: 'Hayır. Demo, NovaShop adında hayalî bir mağazanın sentetik müşteri ve siparişleriyle çalışır ve başka ziyaretçilerle paylaşılır. Oraya gerçek bilgi yazmayın.',
  },
  {
    q: 'Teknik bilgi gerekiyor mu?',
    a: 'Kurulum için Docker’ı kurup birkaç komut çalıştırmanız yeterli; kılavuz adım adım anlatıyor. Kurulumdan sonra her şey tarayıcıdan yönetilir.',
  },
]

export function LandingPage() {
  useEffect(() => {
    wakeBackend()
  }, [])

  return (
    <div className="landing">
      <header className="landing__bar">
        <a className="wordmark landing__brand" href="#top">
          SupportFlow
        </a>
        <nav aria-label="Sayfa bölümleri" className="landing__nav">
          <a href="#nasil-calisir">Nasıl çalışır</a>
          <a href="#guvence">Güvence</a>
          <a href="#kurulum">Kurulum</a>
          <a href="#sss">SSS</a>
        </nav>
        <Link className="button landing__login" to="/login">
          Giriş yap
        </Link>
      </header>

      <main id="top">
        <section className="landing__hero" aria-labelledby="hero-title">
          <div className="landing__pitch">
            <p className="landing__eyebrow">Küçük işletmeler için müşteri destek masası</p>
            <h1 id="hero-title" className="landing__title">
              Yanıtı yapay zekâ hazırlar, son sözü siz söylersiniz.
            </h1>
            <p className="landing__lede">
              SupportFlow, gelen müşteri e-postalarını talebe dönüştürür. Yapay zekâ siparişi ve
              mağaza kurallarınızı kontrol edip bir yanıt taslağı hazırlar. Siz okur, düzeltir,
              onaylar ve gönderirsiniz.
            </p>
            <div className="landing__actions">
              <Link className="button button--primary landing__cta" to="/login">
                Canlı demoyu dene
              </Link>
              <a className="button landing__cta" href={SELF_HOSTING_URL}>
                Kendi sunucuna kur
              </a>
            </div>
            <p className="meta">
              Açık kaynak, erken sürüm. Demo yalnızca sentetik veri kullanır; ilk açılışı bir
              dakikayı bulabilir.
            </p>
          </div>
          <SampleTicket />
        </section>

        <section id="nasil-calisir" className="landing__section" aria-labelledby="how-title">
          <h2 id="how-title" className="landing__heading">
            Bir talep nasıl ilerler
          </h2>
          <ol className="landing__steps">
            {STEPS.map((step, index) => (
              <li key={step.title} className="landing__step">
                <span className="intro__num">{index + 1}</span>
                <h3>{step.title}</h3>
                <p className="muted">{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="guvence" className="landing__section" aria-labelledby="trust-title">
          <h2 id="trust-title" className="landing__heading">
            Yapay zekâ önerir, insan karar verir
          </h2>
          <p className="landing__sub">
            Müşterinize giden her sözün ve siparişteki her değişikliğin sorumlusu sizsiniz.
            SupportFlow bu yüzden bir yardımcı gibi tasarlandı, otomatik pilot gibi değil.
          </p>
          <div className="landing__grid landing__grid--two">
            {GUARANTEES.map((item) => (
              <article key={item.title} className="landing__card">
                <h3>{item.title}</h3>
                <p className="muted">{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing__section" aria-labelledby="features-title">
          <h2 id="features-title" className="landing__heading">
            Neler var
          </h2>
          <div className="landing__grid">
            {FEATURES.map((item) => (
              <article key={item.title} className="landing__feature">
                <h3>{item.title}</h3>
                <p className="muted">{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="kurulum" className="landing__section landing__setup" aria-labelledby="setup-title">
          <div className="landing__setup-main">
            <h2 id="setup-title" className="landing__heading">
              Kendi sunucunuzda, verileriniz sizde
            </h2>
            <p className="landing__sub">
              Her kurulum tek bir işletmeye aittir. Docker yüklü bir bilgisayar ya da sunucu
              yeterli; kurulum sayfası işletme adınızı ve ilk yöneticiyi sorar, ekibinizi de
              oradan eklersiniz.
            </p>
            <pre className="landing__code" aria-label="Kurulum komutları">
              <code>
                {`git clone ${REPO_URL}.git
cd SupportFlow/deploy/selfhost
./init.sh            # Windows: .\\init.ps1
docker compose up -d --build`}
              </code>
            </pre>
            <a href={SELF_HOSTING_URL}>Adım adım kurulum kılavuzu</a>
          </div>
          <aside className="landing__next" aria-labelledby="next-title">
            <h3 id="next-title">Sırada ne var</h3>
            <ul>
              {NEXT_UP.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <a href={ROADMAP_URL}>Yol haritası</a>
          </aside>
        </section>

        <section id="sss" className="landing__section" aria-labelledby="faq-title">
          <h2 id="faq-title" className="landing__heading">
            Sık sorulanlar
          </h2>
          <div className="landing__faq">
            {FAQ.map((item) => (
              <details key={item.q} className="landing__qa">
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landing__closing" aria-labelledby="closing-title">
          <h2 id="closing-title">Bir talebi baştan sona deneyin</h2>
          <p className="muted">
            Demo hesabıyla giriş yapın, bir talebi yapay zekâya inceletin ve öneriyi kendiniz
            onaylayın.
          </p>
          <Link className="button button--primary landing__cta" to="/login">
            Canlı demoyu dene
          </Link>
        </section>
      </main>

      <footer className="landing__footer">
        <span className="wordmark">SupportFlow</span>
        <a href={REPO_URL}>GitHub’da kaynak kodu</a>
        <a href={SELF_HOSTING_URL}>Kurulum kılavuzu</a>
        <Link to="/login">Giriş yap</Link>
      </footer>
    </div>
  )
}

/** A still life of the product: the customer's message, the AI draft and the decision. */
function SampleTicket() {
  return (
    <figure className="desk" aria-labelledby="desk-caption">
      <figcaption id="desk-caption" className="visually-hidden">
        Örnek talep: müşteri adres değişikliği istiyor, yapay zekâ bir yanıt taslağı ve adres
        değişikliği öneriyor, destek uzmanı öneriyi onaylıyor.
      </figcaption>
      <div className="desk__mail" aria-hidden="true">
        <p className="meta">Gelen e-posta · Deniz K.</p>
        <p>
          “Merhaba, ORD-1003 numaralı siparişim henüz yola çıkmadıysa yeni adresime gönderebilir
          misiniz?”
        </p>
      </div>
      <div className="carbon desk__draft" aria-hidden="true">
        <div className="carbon__head">
          <strong>Önerilen yanıt</strong>
          <span className="carbon__tag">Yapay zekâ taslağı</span>
        </div>
        <p>
          Merhaba Deniz, siparişiniz henüz hazırlanıyor, bu yüzden teslimat adresini
          değiştirebiliyoruz. Onaylandığında size haber vereceğiz.
        </p>
        <p className="meta">Kaynak: Adres Değişikliği Politikası, ADRES-1</p>
      </div>
      <div className="label desk__label" aria-hidden="true">
        <div className="label__head">
          <span className="label__title">Adres değişikliği</span>
          <span className="label__order">ORD-1003</span>
        </div>
        <div className="label__body">
          <dl className="label__facts">
            <div>
              <dt>Mevcut</dt>
              <dd className="desk__old">Atatürk Cad. No:12, Konak/İzmir</dd>
            </div>
            <div>
              <dt>Yeni</dt>
              <dd>Kordon Sok. No:15, Bornova/İzmir</dd>
            </div>
          </dl>
          <span className="stamp stamp--executed" style={{ '--stamp-chars': 9 } as CSSProperties}>
            ONAYLANDI
          </span>
        </div>
      </div>
    </figure>
  )
}
