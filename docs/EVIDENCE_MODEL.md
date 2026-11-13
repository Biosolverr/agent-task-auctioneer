# EVIDENCE_MODEL

| Attack | Handling | Residual |
|---|---|---|
| Fabricated or dead URL | pinned as `ok=false`; fewer than `min_sources` reachable -> submission reverts | none |
| Fake page content in leader output | validators re-fetch; excerpt containment < 60% -> no agreement | leader and validators fetching the same lie |
| Page edited after submission | judgment uses the pinned excerpt, not the live page | pinned text is at most 1200 chars per URL |
| Non-HTTPS, IP literal, localhost, userinfo, port, `.internal`, `.local`, bare hosts | rejected in `submit_deliverable` (`test_evidence.py`) | DNS names that resolve to private addresses: only the validator network can stop these (L3) |
| Domain tricks (`evil-site1.org`) | allow-list matches the host or a true subdomain | none found |
| Duplicate sources | distinct URLs required | different URLs with copied content (not detected) |
| Oversized pages | body cut at 200,000 bytes, excerpt at 1,200 chars, URL at 300 chars, max 3 URLs | none |
| Script/style/markup | removed; `<` and `>` replaced in stored text so a tag cannot be closed | none |
| Prompt injection in pages or deliverable | content sits inside `<untrusted>` blocks; model output is reduced to per-criterion flags; verdict derived by code; model cannot change settlement | a model may still be swayed on individual flags; protected by validator re-run and one appeal |
| Stale/fake publication dates | not verified; judged only if the page text states them | L4 |
