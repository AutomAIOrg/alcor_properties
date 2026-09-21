# Protección del login con Tailscale Funnel

Cada intento de login, incluido el correcto, consume el cupo de IP y usuario.
Las cuentas existentes comparten contador por ID; los nombres desconocidos se
normalizan. Los contadores viven en MySQL (InnoDB), son compartidos entre
procesos y usan la hora de la base de datos. Por defecto se permiten 5 intentos
cada 900 segundos; ambos valores se configuran con `LOGIN_RATE_LIMIT_*`.
Aplicar `alembic upgrade heads` antes de iniciar la API. Si falla la base de
datos, el login se deniega.

El despliegue sigue `deploy/TAILSCALE_FUNNEL.md`: Funnel termina HTTPS en el
host y reenvía a Caddy por `127.0.0.1:8080`. No se publican puertos HTTPS de
Caddy ni se necesita un segundo archivo Compose.

El Compose añade la red privada `auth_proxy` (`172.30.253.0/29`) sin
cambiar la red Docker existente de los otros servicios. Caddy está solo en
esa red con la IP `172.30.253.3`; el backend mantiene su red habitual y se
conecta también a `auth_proxy`. Funnel sigue entrando por el puerto del host
`127.0.0.1:8080`. Caddy confía únicamente en el gateway de esa red
(`172.30.253.1/32`) y extrae la IP de `X-Forwarded-For` de derecha a izquierda.
Antes de enviarla al backend, sustituye la cabecera por la IP verificada y
elimina `X-Real-IP`. El backend solo acepta esa cabecera cuando el peer
inmediato es Caddy (`172.30.253.3/32`); Uvicorn no reescribe la IP.

Antes de desplegar, comprobar que `172.30.253.0/29` no se solapa con ninguna
red del VPS. Verificar también que Caddy recibe las conexiones de Funnel desde
`172.30.253.1`, ya que la traducción del puerto del host depende de Docker.
Si alguna IP difiere, corregir los valores exactos de Caddy y Compose antes
de activar el límite. No confiar en redes privadas completas.

Comprobar el login desde dos redes externas, con y sin cabeceras
`X-Forwarded-For` y `X-Real-IP` falsificadas. Confirmar que cada IP tiene su
propio cupo, que el cupo por usuario se comparte y que el exceso devuelve
HTTP 429 con `Retry-After`.

Los contadores contienen claves hash. Eliminar periódicamente filas caducadas,
por ejemplo desde una tarea programada en la base de datos:
`DELETE FROM auth_login_limits WHERE window_start < UNIX_TIMESTAMP() - 86400;`
La retención debe superar la ventana configurada.
