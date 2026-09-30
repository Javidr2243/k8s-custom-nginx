# Despliegue en un VPS (Docker + Caddy)

Arquitectura: **Caddy** (HTTPS automático) → **nginx sin privilegios** (sitio estático) en una red interna de Docker.
El servidor **jala** la imagen: un temporizador de systemd revisa cada 5 minutos la etiqueta `prod` en GHCR,
**verifica la firma** (cosign) y la despliega fijada por digest. GitHub nunca tiene llaves del servidor.

```
merge a main → CI: pruebas → imagen → Trivy → push → firma + SBOM + procedencia
            → job "promote" (requiere aprobación en el Environment "production") → etiqueta prod
VPS (cada 5 min): digest de prod → cosign verify → docker compose up --wait → si falla, regresa al anterior
```

## 1. Servidor (una sola vez)

Probado con Ubuntu 24.04 LTS / Debian 12. 1 vCPU y 1 GB de RAM sobran.

```sh
# Actualizaciones automáticas de seguridad (con reinicio en ventana nocturna)
sudo apt update && sudo apt -y upgrade
sudo apt -y install unattended-upgrades fail2ban ufw
sudo dpkg-reconfigure -plow unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";' | sudo tee /etc/apt/apt.conf.d/52reboot

# SSH: solo llaves, sin root, solo tu usuario administrador
sudo sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/; s/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
echo 'AllowUsers admin' | sudo tee /etc/ssh/sshd_config.d/10-allow.conf   # cambia "admin" por tu usuario
sudo systemctl restart ssh

# Firewall: 80/443 para todos, 22 solo desde tu IP (o usa Tailscale/WireGuard y cierra 22 al público)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from TU.IP.PUBLICA to any port 22 proto tcp
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
sudo ufw enable
```

> **Importante:** Docker publica puertos por fuera de ufw. Por eso en `docker-compose.yml` **solo Caddy**
> publica puertos (80/443). No agregues `ports:` a otros servicios.

### Docker y cosign

```sh
# Docker Engine desde el repositorio oficial: https://docs.docker.com/engine/install/
# cosign (verifica firmas): https://docs.sigstore.dev/cosign/system_config/installation/
cosign version
```

### Usuario de despliegue y archivos

```sh
sudo useradd --system --home-dir /var/lib/gdmty-deploy --create-home --shell /usr/sbin/nologin gdmty-deploy
sudo usermod -aG docker gdmty-deploy        # docker = equivalente a root: este usuario solo corre deploy.sh
sudo install -d -o gdmty-deploy -g gdmty-deploy -m 750 /opt/gdmty
sudo install -o root -g root -m 755 deploy/deploy.sh /opt/gdmty/deploy.sh
sudo install -o root -g root -m 644 deploy/docker-compose.yml deploy/Caddyfile /opt/gdmty/
sudo install -o gdmty-deploy -g gdmty-deploy -m 600 deploy/env.example /opt/gdmty/.env
sudoedit /opt/gdmty/.env                    # pon tu DOMINIO y ACME_EMAIL
sudo install -m 644 deploy/gdmty-deploy.service deploy/gdmty-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gdmty-deploy.timer
```

## 2. DNS

- Registro `A` (y `AAAA` si tienes IPv6) de tu dominio y de `www` apuntando al VPS.
- Registro `CAA` para que solo Let's Encrypt emita certificados: `tudominio. CAA 0 issue "letsencrypt.org"`.
- Opcional: Cloudflare en modo proxy (protección DDoS, oculta la IP). Si lo usas, limita 80/443 en ufw a
  [los rangos de Cloudflare](https://www.cloudflare.com/ips/).

## 3. GitHub (una sola vez)

1. **Paquete público:** en *Packages → k8s-custom-nginx → Package settings*, cambia la visibilidad a *Public*
   (el VPS no necesita credenciales para descargarla).
2. **Environment `production`:** *Settings → Environments → New environment → production* y agrega
   *Required reviewers* (tú). Así ninguna imagen llega a producción sin aprobación.
3. **Protección de `main`:** requerir PR con 1 aprobación, requerir los checks de CI, prohibir force push.
4. **Seguridad:** activa *Secret scanning*, *Push protection*, *Dependabot alerts* y *Private vulnerability reporting*.

## 4. Primer despliegue

Haz merge a `main`, aprueba el job **Promote to production** en Actions y espera ≤ 5 minutos (o corre
`sudo systemctl start gdmty-deploy.service`). Revisa:

```sh
journalctl -u gdmty-deploy.service -n 50
curl -I https://tudominio/      # debe incluir strict-transport-security y content-security-policy
```

## Operación

- **Estado / registros:** `journalctl -u gdmty-deploy.service`, `docker compose -f /opt/gdmty/docker-compose.yml ps`.
- **Revertir manualmente:** los últimos 3 digests están en `/var/lib/gdmty-deploy/history`. Para volver a uno,
  vuelve a etiquetar ese digest como `prod` (job *promote* o `docker buildx imagetools create`); el
  temporizador lo verifica y despliega. El script ya revierte solo si el healthcheck falla.
- **Respaldos:** el servidor no guarda estado; todo se reconstruye desde git y GHCR. Solo conviene respaldar
  `/opt/gdmty/.env` y el volumen `gdmty_caddy_data` (certificados).
- **Monitoreo:** un chequeo externo (UptimeRobot, healthchecks.io) contra `https://tudominio/`, alerta de disco
  y de vencimiento del certificado.
- **Prueba de la firma:** `cosign verify --certificate-identity-regexp '^https://github\.com/javidr2243/k8s-custom-nginx/\.github/workflows/ci\.yml@refs/heads/main$' --certificate-oidc-issuer https://token.actions.githubusercontent.com ghcr.io/javidr2243/k8s-custom-nginx:prod`
  debe decir que la firma es válida; con una imagen sin firmar debe fallar y `deploy.sh` no la despliega.
