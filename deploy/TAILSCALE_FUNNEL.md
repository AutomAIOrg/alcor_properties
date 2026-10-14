# Publicación con Tailscale Funnel

Tailscale Funnel termina HTTPS en el host de la VPS y envía las peticiones a
`http://127.0.0.1:8080`. Docker solo publica Caddy en esa dirección; Caddy
escucha HTTP en el puerto 80 dentro del contenedor. No hace falta configurar
certificados ni un dominio en Caddy.

## Preparación

1. Instalar y autenticar Tailscale en el host. Habilitar MagicDNS, HTTPS y
   Funnel para el nodo en el tailnet.
2. Mantener `.env.production` fuera de Git. En ese archivo, usar el nombre real
   del nodo para `FRONTEND_URL` y `CORS_ORIGINS`; conservar las credenciales y
   demás valores existentes al actualizar el repositorio. La plantilla
   `.env.production.example` no debe copiarse encima del archivo en uso.
3. Levantar el stack con `docker compose -f docker-compose.prod.yml up -d --build`.

## Comprobación y publicación

```bash
curl -f http://127.0.0.1:8080/health
sudo tailscale funnel --bg 8080
sudo tailscale funnel status
curl -f https://TU_NODO.TU_TAILNET.ts.net/health
```

`--bg` mantiene la publicación tras reiniciar Tailscale o la VPS. La
configuración de Funnel vive en el host y debe repetirse al reconstruirlo desde
cero. El puerto público HTTPS de Funnel es 443; el 8080 solo escucha en el
loopback de la VPS.

Si Traefik también funciona en el host, comprobar sus direcciones de escucha
y las de Tailscale antes de cambiar la asignación del puerto 443. No es
necesario mover Traefik de IP si no existe un conflicto real.

Cuando se habilite el límite de login por IP, comprobar desde dos redes
externas que las solicitudes se contabilizan por cliente y que una cabecera
`X-Forwarded-For` enviada por el cliente no altera la IP elegida. La unión
Funnel → Caddy → FastAPI no preserva de forma segura esa identidad por el
simple hecho de publicar el puerto 8080; cada proxy debe confiar solo en su
salto anterior verificado. No confiar en redes privadas completas.
