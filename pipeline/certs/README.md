# Intermediate certificates

Some official sites send an incomplete TLS chain (they omit the intermediate certificate).
Instead of disabling verification, the pipeline adds these **intermediates** to the system trust store.
They are never trust roots in their own right: every chain still ends at a root in the system store.

| Certificate | Used by | Source |
|---|---|---|
| Sectigo Public Server Authentication CA DV R36 | www.stacatarina.gob.mx | AIA `crt.sectigo.com` of the site's certificate |
| Let's Encrypt YR1 | *.hacienda.gob.mx, transparenciapresupuestaria.gob.mx | https://letsencrypt.org/certs/gen-y/int-yr1.pem |
| ISRG Root YR (cross-signed by ISRG Root X1) | same, to reach X1 | https://letsencrypt.org/certs/gen-y/root-yr-by-x1.pem |

Every entry in `intermediates.pem` includes its SHA-256 fingerprint and expiry date. CI warns 30 days
before any of them expires (`python -m gdmty certs`).
