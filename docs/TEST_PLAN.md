# Test planı

Gereksinimlerin nasıl doğrulandığı. Backend testleri gerçek bir PostgreSQL test veritabanında çalışır (her test geri alınan bir transaction içinde); hiçbir test ücretli LLM API'sini çağırmaz.

```bash
cd backend && uv run poe check        # lint, format, tip kontrolü, 200 test
cd backend && uv run poe eval         # senaryo eval'leri (sahte model); Gemini için --live
cd frontend && npm test               # 20 bileşen testi (Vitest + Testing Library)
```

## Senaryolar (docs/REQUIREMENTS.md bölüm 5)

| Senaryo | Doğrulayan |
|---|---|
| S1 Siparişim nerede | `test_analysis_records_every_graph_step` (kural kontrolü, doğrulanmış kanıt, aksiyon yok) |
| S2 Hasarlı ürün → iade talebi | `test_allowed_refund_cases_propose_a_refund_request`, `test_agent_user_cannot_decide_a_refund_but_admin_can` |
| S3 Adres değişikliği | `test_allowed_address_change_produces_a_pending_proposal`, `test_ticket_to_ai_proposal_to_approval_to_single_change` |
| S4 Bilinmeyen sipariş | `test_unknown_and_foreign_orders_lead_to_needs_info`, `test_order_request_without_a_usable_order_asks_for_it_and_skips_policy` |
| S5 İade süresi dışında iade | `test_refund_outside_the_return_window_gets_no_proposal` |
| S6 Önceki talep | `test_previous_tickets_reach_the_draft_for_follow_ups` |

## Senaryo eval'leri

`evals/scenarios.jsonl`, 13 talebi düz veri olarak tanımlar: S1–S6, P0 güvenlik senaryoları (TC-05, TC-06, TC-07/TC-18, TC-10; TC-10 hem Türkçe hem İngilizce) ve birkaç uç durum. Talepler Türkçedir. Her birinin kendi müşterisi ve siparişleri vardır ve gerçek akıştan geçer (kuyruğa alınan çalıştırma, LangGraph, veritabanı araçları, kurallar, öneri). Kontroller iki türlüdür:

- **Kritik** (her model için sağlanmalı): talep durumu, hangi yazma aksiyonunun önerildiği (ya da hiçbirinin), önerinin müşterinin kendi siparişini hedeflemesi, yeni adresin müşterinin yazdığı adres olması, doğrulanmış kanıtın yalnızca müşterinin siparişlerinden gelmesi, yanıtta başka müşterinin verisinin ya da enjekte edilmiş değerlerin bulunmaması, politika atıflarının yalnızca getirilen maddelere yapılması.
- **Kalite** (sahte model için sağlanmalı, canlı model için ölçülür): kategori, atıf yapılan kanıt, takip yanıtının önceki talebe değinmesi, doğru politika maddesine atıf (`cites_clause_in`).

Eval'ler başlamadan önce bilgi tabanı sahte embedder'la indekslenir; böylece getirme deterministik kalır ve yalnızca test edilen model değişir.

`tests/integration/test_evals.py` CI'da her senaryoyu sahte modelle çalıştırır ve yanlış bir beklentinin başarısızlık olarak raporlandığını da kanıtlar. `uv run poe eval --live` aynı dosyayı gerçek modeli ölçmek için Gemini'ye karşı çalıştırır (rate limit için aralıklı); CI'da asla çalışmaz.

Canlı sonuçlar (her biri tek çalıştırma; sonuçlar çalıştırmadan çalıştırmaya değişebilir):

| Tarih | Model | Prompt sürümü | Tamamen geçen | Tüm kritik kontrolleri geçen |
|---|---|---|---|---|
| 2026-11-03 | `gemini-3.5-flash-lite` | `graph-v2` (İngilizce set) | 12/12 | 12/12 |
| 2026-11-03 | `gemini-3.5-flash-lite` | `graph-v3` (Türkçe set, 13 senaryo) | 13/13 | 13/13 |
| 2026-11-03 | `gemini-3.5-flash-lite` | `graph-v4` (politika atıflarıyla) | 12/13 | 13/13 |

`graph-v4` notu: tek kalite uyarısı `TC-10-prompt-injection-english`. Model mesajı iade talebi olarak sınıflandırdığı için İade ve İstisnalar politikaları birlikte getirildi ve taslak `IADE-2`'ye atıf yaptı (beklenen `ISTISNA-2/3`). Atıf getirilen bir maddeye yapıldığı için kritik kontrol geçti; aksiyon önerilmedi.

## Politika getirme kalitesi

`evals/policy_retrieval.jsonl` 20 soru içerir: bilgi tabanındaki maddeleri hedefleyen 18 doğal personel sorusu ve grafın gerçekte gönderdiği türden 2 kural gerekçesi (politika filtresiyle). `uv run poe eval-rag` bilgi tabanını test veritabanında, geri alınan bir transaction içinde indeksler ve her soruyu arar:

- **hit@k:** beklenen maddelerden birinin ilk k sonuç içinde olduğu soruların oranı;
- **MRR:** beklenen ilk maddenin sırasının tersinin ortalaması.

| Tarih | Embedder | hit@1 | hit@3 | MRR |
|---|---|---|---|---|
| 2026-11-03 | `fake-embedding@768` (çevrimdışı) | 0.80 | 0.95 | 0.86 |
| 2026-11-03 | `gemini-embedding-2@768` | 0.90 | 1.00 | 0.94 |

Sahte embedder'ın tek kaçırdığı soru "Kargoda kırılan bir ürün": kelime kökü yöntemi "kargo"yu adres maddesine bağlıyor, eş anlamlıları bilmiyor. `tests/integration/test_retrieval_eval.py` çevrimdışı sonucun bu taban değerlerin altına düşmesini CI'da yakalar; canlı ölçüm (`--live`) elle çalıştırılır.


## Test matrisi (ROADMAP §6)

| ID | Durum | Kapsam | Doğrulayan |
|---|---|---|---|
| TC-01 | Kargoya verilmemiş siparişte adres değişikliği → bekleyen öneri | Kapsandı | `test_allowed_address_change_produces_a_pending_proposal` |
| TC-02 | Onaylandı → adres bir kez güncellenir, denetim kaydı yazılır | Kapsandı | `test_approval_executes_the_change_exactly_once`, `test_audit_trail_is_redacted_admin_only_and_append_only` |
| TC-03 | Reddedildi → adres değişmez | Kapsandı | `test_reject_ends_the_proposal_without_any_change` |
| TC-04 | İki kez onaylandı → tek aksiyon | Kapsandı | `test_second_approval_is_rejected_and_changes_nothing`, `test_idempotency_key_prevents_a_second_effect_even_if_called_again` |
| TC-05 | Sipariş onaydan önce kargoya verildi → gerekçeyle engellenir | Kapsandı | `test_order_shipped_after_proposal_blocks_the_address_change` |
| TC-06 | Bilinmeyen sipariş → `needs_info`, hiçbir şey uydurulmaz | Kapsandı | `test_unknown_and_foreign_orders_lead_to_needs_info` |
| TC-07 | Başka müşterinin siparişi → sızıntı yok | Kapsandı | `test_database_tools_are_scoped_to_one_customer`, `test_scoped_lookup_treats_another_customers_order_as_missing` |
| TC-08 | Geçersiz model JSON'ı → kontrollü hata | Kapsandı | `test_invalid_model_output_is_a_controlled_failure`, `test_invalid_model_output_fails_the_run_safely_and_allows_retry` |
| TC-09 | LLM zaman aşımı → yeniden deneme, ardından başarısız çalıştırma | Kapsandı | `test_transient_errors_are_retried_with_growing_backoff`, `test_llm_outage_fails_the_run_with_a_stable_code` |
| TC-10 | Prompt injection: "yönetici gibi davran" | Kapsandı | `test_prompt_injection_changes_nothing_but_the_analysis` |
| TC-11 | Bir kural kaynağında kötü niyetli talimatlar | Kapsandı | `test_instructions_inside_a_policy_document_change_nothing`, `test_customer_text_inside_facts_cannot_close_the_facts_block` |
| TC-12 | Webhook tekrarı | Faz 9 (n8n) | |
| TC-13 | Bir onay beklerken yeniden başlatma | Kapsandı | `test_ticket_to_ai_proposal_to_approval_to_single_change`, `test_restart_between_decision_and_execution_is_reconciled_once` |
| TC-14 | Yetkisiz siparişle MCP aracı | Faz 8 (MCP) | |
| TC-15 | Kural sürümü değişti | Kapsandı: yeni sürüm eskisinin yerini alıyor, arama (dolayısıyla taslağa giden alıntılar) yalnızca güncel sürümü görüyor | `test_a_new_version_supersedes_the_old_one_for_search`, `test_editing_a_document_without_a_new_version_is_refused` |
| TC-16 | Veritabanına erişilemiyor → `/ready` 503 | Kapsandı | `test_ready_returns_503_when_database_is_unreachable` |
| TC-17 | Eşzamanlı iki analiz → biri çalışır | Kapsandı | `test_second_analysis_request_while_queued_is_rejected`, `test_database_allows_only_one_active_run_per_ticket` |
| TC-18 | Model başka müşterinin sipariş kimliğini verir | Kapsandı | `test_model_cannot_point_the_agent_at_an_order_the_customer_never_mentioned`, `test_database_tools_are_scoped_to_one_customer` |
| TC-19 | Destek uzmanı iadeyi onaylar → 403 | Kapsandı | `test_agent_user_cannot_decide_a_refund_but_admin_can` |
| TC-20 | Çalıştırma sırasında yeniden başlatma | Kapsandı | `test_restart_marks_unfinished_runs_as_interrupted` |

## Frontend (Faz 6 kabul kriterleri)

| Gereksinim | Doğrulayan |
|---|---|
| Boş liste anlamlı bir mesaj gösterir | `TicketsPage.test.tsx`: boş gelen kutusunu açıklar |
| API hatası asla başarı olarak gösterilmez | `TicketsPage.test.tsx`: net hata; `ProposalCard.test.tsx`: başarı yerine çakışma |
| Çift gönderim engellenir; gösterilen sürüm gönderilir | `ProposalCard.test.tsx`: uygulanırken ikinci tıklamayı engeller |
| Yetkisiz roller karar butonu görmez (API de reddeder: TC-19) | `ProposalCard.test.tsx`: karar butonu yok |
| Yanlış giriş bilgileri açıklanır | `LoginPage.test.tsx` |
| Kural sonucunun dayandığı politika maddesi kaynağıyla gösterilir; yalnızca atıf yapılan maddeler "Dayanağı" olarak sunulur | `TicketParts.test.tsx` |
| Genel bakış sayıları filtrelenmiş listeye bağlanır | `DashboardPage.test.tsx`: her durum sayısını bağlar |
| Rol farkı görünür: destek uzmanları iadeleri "yönetici bekliyor" olarak görür, yöneticiler karar verir ve denetim kaydını görür | `DashboardPage.test.tsx`: destek uzmanı denetim kaydını asla istemez, yönetici her kararı alır; `ProposalCard.test.tsx`: "Yalnızca yönetici" işareti |
| Demo verisi iki rolü de iş başında gösterir; gerçek analiz/onay akışından ve ücretli model olmadan | `test_seed.py::test_demo_activity_shows_both_approval_roles_and_is_idempotent` |

Görsel kontroller 1440px ve 390px genişlikte ekran görüntüleriyle yapılır (giriş, destek uzmanı ve yönetici olarak genel bakış, talepler, her durumda talep detayı, onaylar, karardan sonraki mühür).

## Dokümantasyon

| Gereksinim | Doğrulayan |
|---|---|
| Linkler ve anchor'lar kırık değil, `API.md` uygulamanın uç noktalarıyla aynı, ADR numaraları tanımlı, her doküman haritada | `test_docs.py::test_repository_documentation_has_no_drift` (her CI çalıştırmasında; kurallar [docs/README.md](README.md#otomatik-kontroller)) |
| Kontrol, bozuk link, eski anchor, eksik/fazla uç nokta, tanımsız ADR ve haritada olmayan dokümanı gerçekten yakalıyor | `test_docs.py` içindeki diğer testler |

## Bilinen eksikler

- CI'da henüz tarayıcıda uçtan uca test yok (Faz 10).
- Satır kilitleri ve benzersiz kısıtların ötesinde yük ya da eşzamanlılık testi yok.
- Ücretsiz API kotası içinde kalmak için canlı model eval'leri her değişiklikte değil, elle çalıştırılır (`poe eval --live`).
