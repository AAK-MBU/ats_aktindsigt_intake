# ats_aktindsigt_intake

ATS-proces, der sender OS2Forms-svar på aktindsigts to webforms videre til aktindsigt-portalen. Processen tager items fra intake-køen, henter svaret og dets vedhæftninger fra OS2Forms og sender det til portalens `POST /api/intake/sager`. Kroppen har samme form, som OS2Forms' Remote post-handler bruger.

Processen bygger på [ats-process-framework](https://github.com/AAK-MBU/ats-process-framework).

## Flow

```
OS2Forms ◄── poll ── os2forms-polling-service ──► ATS intake-kø (reference = svarets uuid)
                                                        │  workqueue-trigger
                                                        ▼
                    --process  pr. item:  hent svar + vedhæftninger i OS2Forms
                                          byg Remote post-kroppen
                                          POST /api/intake/sager ──► aktindsigt
```

| Trin | Flag | Rolle |
|---|---|---|
| Populate | `--queue` | no-op: polling-servicen fylder køen |
| Process | `--process` | `processes/handle_item.handle_item` pr. item |
| Finalize | `--finalize` | no-op |

### Pr. item
1. Webformens id læses af itemets data: `webformId` fra en payload med kun referencer, ellers `entity.webform_id[0].target_id` fra et rå webform_rest-svar. Kun webforms i `WEBFORMS` behandles.
2. Svaret hentes friskt fra OS2Forms med itemets reference (svarets uuid). Itemets egne data bruges ikke som formulardata.
3. For hvert filfelt i webformens konfiguration, der har en værdi (filens id), hentes filen via linket i `data.linked.<element>.<fil-id>`. Filnavnet tages af URL'ens sidste led, mime-typen af `mime_type`. `data.attachments` (OS2Forms' genererede kvitteringer) og `data.linked` sendes ikke videre.
4. Kroppen bygges af `processes/remote_post.build_form_items` som `application/x-www-form-urlencoded`:
   - `webform_id` og formularens felter med elementnavnene
   - lister som `navn[0]` og sammensatte elementer som `navn[nøgle]`
   - filer som blokken `_<element>[id|name|mime|data]` med base64 i `data`
   - `submission_uuid` til sidst
5. Kroppen sendes med headeren `X-API-Key`.

### Udfald

| Svar | Itemets status | Besked |
|---|---|---|
| Aktindsigt 201 | completed | `Sag <id> oprettet i aktindsigt` |
| Aktindsigt 200 (uuid'en er modtaget før) | completed | `Allerede modtaget i aktindsigt som sag <id>` |
| Aktindsigt 422 | pending user | aktindsigts `detail` med `loc` og `msg`, renset for CPR-lignende tal |
| Ukendt eller manglende webform, intet uuid, svaret eller en fil findes ikke i OS2Forms, eller et udfyldt filfelt uden link | pending user | årsagen |
| OS2Forms eller aktindsigt kan ikke spørges (401/403/5xx/timeout/netværk) | failed | fejlmail via frameworket |

Formularens indhold (CPR, filindhold) indgår hverken i logs, i item-beskeder eller i fejlmails. Når frameworket logger en fejl, logges kun itemets reference.

## Kør

Kræver Python 3.13 og [uv](https://docs.astral.sh/uv/). `DBCONNECTIONSTRINGPROD` bruges gennem pyodbc og kræver en ODBC-driver til SQL Server.

```sh
uv sync
cp .env.example .env                     # udfyld værdierne
uv run python main.py --process
```

## Konfiguration

### `ats_framework/processes/intake_config.py`

| Navn | Betydning |
|---|---|
| `OS2FORMS_BASE_URL`, `OS2FORMS_CREDENTIAL` | OS2Forms-instansen og navnet på den credential, der har api-key'en |
| `AKTINDSIGT_BASE_URL` | Portalens backend. `/api/intake/sager` lægges til |
| `AKTINDSIGT_CREDENTIAL` | Navnet på den credential, der har aktindsigts intake-API-nøgle |
| `HTTP_TIMEOUT` | Timeout i sekunder pr. HTTP-kald |
| `WEBFORMS` | `webform_id` → `WebformConfig(filfelter={<OS2Forms-element>: <filblok>})` |

Værdier med præfikset `UDFYLDES_` er pladsholdere. `validate_config()` afviser dem ved starten af `--process`.

### Miljøvariabler

| Variabel | Påkrævet | Betydning |
|---|---|---|
| `ATS_URL`, `ATS_TOKEN` | ja | ATS-API'et |
| `ATS_WORKQUEUE_OVERRIDE` | lokalt | Id på intake-køen. I drift vælges den af ATS-sessionen. |
| `DBCONNECTIONSTRINGPROD` | ja | ODBC-forbindelse til RPA-databasen |
| `AARHUS_ROOT_CERT_PEM` | nej | PEM med ATS' CA. Tilføjes til de offentlige rodcertifikater. |

### RPA-databasen
- **Credentials:** `os2_api` (OS2Forms' api-key) og den credential, `AKTINDSIGT_CREDENTIAL` peger på (aktindsigts intake-nøgle).
- **Konstanter til frameworkets fejlmail:** `Error Email`, `Email Friend`, `smtp_server`, `smtp_port`.

## Datakilder

| Kilde | Adgang |
|---|---|
| OS2Forms `GET /webform_rest/{webform_id}/submission/{uuid}` | svaret (`data`, `data.linked`) |
| OS2Forms: vedhæftningens URL | filens bytes |
| Aktindsigt `POST /api/intake/sager` | opretter sagen, svarer `{"sagId"}` |
| `[rpa].[Credentials]`, `[rpa].[Constants]` via `mbu_rpa_core.RPAConnection` | api-nøgler og mail-opsætning |

## Projektstruktur

```
main.py                        entrypoint: --queue / --process / --finalize
ats_framework/core/            frameworkets løkker; delegerer til processes/
ats_framework/helpers/         OS2Forms- og aktindsigt-kald, RPA-opslag, TLS
ats_framework/processes/       intake_config, remote_post, handle_item
tests/                         pytest; aktindsigt_reference.py spejler aktindsigts læsning af kroppen
```

## Test

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Testene kører isoleret: OS2Forms-, aktindsigt- og databasekald monkeypatches. `tests/aktindsigt_reference.py` er en kopi af aktindsigts `parse_felter` og filblok-afkodning. Testene bruger den til at vise, at kroppen læses som Remote post-kroppen. CI kører ruff og kræver, at `version` i `pyproject.toml` er bumpet på pull requests til `main`.

## Kendte begrænsninger

- Elementnavnet `upload_fuldmagt` i `WEBFORMS` er udledt af Remote post-blokken `_upload_fuldmagt` og er ikke verificeret mod webformens konfiguration i OS2Forms.
- Formen på webform_rest-svarets `data` for sammensatte elementer og filfelter er udledt af os2forms-polling-service og aktindsigts tests, ikke af et produktionssvar.
- Remote post kan også have sendt svarets øvrige entitetsfelter (fx `sid`, `created`); det er ikke verificeret. Kroppen her har kun `webform_id`, formularens felter, filblokkene og `submission_uuid`. Aktindsigt læser ikke de øvrige felter.
