# it-ops-scripts

[![CI](https://github.com/islamelsabahy/it-ops-scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/islamelsabahy/it-ops-scripts/actions/workflows/ci.yml)

**EN** — Small, dependency-free scripts for day-to-day IT operations: network audit, CCTV/PBX health check, backup verification, and Active Directory joiner/leaver automation. Python 3.9+ standard library only. All sample data is fictional (RFC 5737 documentation IP ranges).

**AR** — سكربتات صغيرة وعملية لتشغيل الـ IT اليومي: فحص الشبكة، فحص حالة الكاميرات والسنترال، التأكد من نجاح النسخ الاحتياطي، وأتمتة تعيين وإنهاء خدمة المستخدمين على Active Directory. بايثون بدون أي مكتبات خارجية، وكل بيانات العينة وهمية.

---

## What's inside / المحتوى

| Tool | What it does | الوظيفة |
|---|---|---|
| `itops.network_audit` | Ping + expected-port check for a host CSV, writes CSV and Markdown reports | فحص ping والبورتات المتوقعة وتقرير جاهز |
| `itops.device_health` | Health report for NVR, cameras, PBX and access controllers, grouped by site | تقرير أعطال الأجهزة لكل موقع |
| `itops.backup_verify` | Checks newest backup age and size; alerts via Telegram or email on problems | يتأكد إن آخر باك أب حديث وحجمه منطقي ويبعت تنبيه |
| `powershell/New-ADUsersFromCsv.ps1` | Create AD users from an HR CSV (password never stored) | إنشاء مستخدمين من ملف HR |
| `powershell/Disable-ADUsersFromCsv.ps1` | Offboard users: disable, stamp, optionally strip groups and move OU. Never deletes | إنهاء الخدمة بدون حذف |

## Quick start / تشغيل سريع

```bash
python -m itops.network_audit  --hosts   sample-data/hosts.example.csv   --out reports
python -m itops.device_health  --devices sample-data/devices.example.csv --out reports
python -m itops.backup_verify  --jobs    sample-data/backup_jobs.example.csv --notify telegram
python -m unittest discover -s tests
```

Exit codes make the tools easy to schedule (cron, Task Scheduler): `0` healthy, `1` warning/degraded, `2` failure/down.

```powershell
$pw = Read-Host "Initial password" -AsSecureString
.\powershell\New-ADUsersFromCsv.ps1 -CsvPath .\sample-data\joiners.example.csv `
    -OuPath "OU=Staff,DC=example,DC=local" -UpnSuffix "example.local" -InitialPassword $pw -WhatIf
```

Always run the AD scripts with `-WhatIf` first. / شغّل سكربتات AD بـ `-WhatIf` الأول دايماً.

## Alerts / التنبيهات

Settings come from environment variables only, never from files in the repo:

- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Email: `SMTP_HOST`, `SMTP_FROM`, `SMTP_TO` (optional `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`)

## Safety notes / ملاحظات أمان

- Do not commit real inventories, IPs, usernames, tokens, or reports. `reports/` and `.env` are git-ignored.
- The network tools only ping and open TCP connections; they do not scan ranges or send credentials.
- Test the AD scripts in a lab OU before production.

## Roadmap

- [ ] SNMP checks for switches and UPS
- [ ] Windows Task Scheduler / cron examples in `docs/`
- [ ] SSL certificate expiry checker
- [ ] HTML report option

## License

MIT
