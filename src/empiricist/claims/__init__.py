"""The v1 claim ledger: git-tracked claim files, a hash lock, standing, `check`.

Core, domain-free (charter section 5): this package imports nothing from
`domain/`, `search/` or `campaign/`. The SQLite ledger stays local campaign
state; the files under `claims/` are the canonical, committed record.
"""
