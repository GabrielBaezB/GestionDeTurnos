# Manual de Despliegue en Producción 🚀

Este documento detalla cómo llevar **GestionDeTurnos** a un entorno productivo, cubriendo dos arquitecturas principales dependiendo del acceso requerido por sus clientes (Intranet vs Web Pública).

---

## 🏗 Arquitectura 1: Despliegue en Intranet (Red Local)

Ideal para sucursales físicas, clínicas o municipalidades donde **todas las pantallas** (Kiosco, Operadores y Monitor TV) están conectadas al mismo router o red WiFi local.

### Ventajas
* **Máxima Privacidad:** La base de datos y la API no están expuestas a Internet.
* **Cero Costo de Hosting:** El servidor puede ser una PC física corriendo en la oficina.
* **Baja Latencia:** Los flujos SSE (Server-Sent Events) del Monitor actualizan al instante.

### Pasos de Despliegue

1. **Preparar el Servidor Local**
   * Computadora con Windows/Linux (Ubuntu Server recomendado).
   * Asignar una **IP Privada Estática** en el router (ej. `192.168.1.100`).
   * Instalar [Docker](https://docs.docker.com/get-docker/) y Docker Compose.

2. **Clonar e Iniciar el Proyecto**
   Abre una terminal en el servidor:
   ```bash
   git clone https://github.com/GabrielBaezB/GestionDeTurnos.git
   cd GestionDeTurnos
   ```

3. **Configurar el Entorno**
   ```bash
   cp .env.example .env
   # Edita .env con tus contraseñas seguras
   nano .env
   ```
   *Nota: No es estricto configurar el bloque CORS en Intranet, puede quedar con los comodines por defecto.*

4. **Levantar el Servicio**
   ```bash
   docker-compose up -d
   ```

5. **Acceder desde los Dispositivos (Tablets, TVs, Operadores)**
   Abre el navegador en cualquier computadora de la oficina y apunta a la IP estática del servidor:
   * **Portal Kiosco:** `http://192.168.1.100:8000/kiosk`
   * **Supervisor:** `http://192.168.1.100:8000/admin`
   * **Monitor TV:** `http://192.168.1.100:8000/monitor`

---

## 🌍 Arquitectura 2: Despliegue en Internet (Web Pública)

Ideal si deseas operar un sistema multi-sucursal remoto, atender a clientes desde sus celulares en casa (Filas Virtuales), o tener a los operadores trabajando vía VPN/remoto.

### Ventajas
* Accesibilidad global.
* Integración futura sencilla con WhatsApp APIs u otras pasarelas.

### Advertencias de Seguridad Críticas
Al exponer la API `FastAPI` y base de datos de tickets al exterior, es **obligatorio** el uso de un túnel seguro **HTTPS**. Sin HTTPS:
1. Las contraseñas viajan en texto plano.
2. Los navegadores modernos **bloquearán** los micrófonos (necesarios para el sonido del `monitor.html`) si no estás en un origen seguro.

### Pasos de Despliegue (con Proxy Inverso)

1. **Obtener un Servidor VPS**
   * Contrata un servidor virtual (DigitalOcean, AWS, Linode) con al menos 2 CPUs y 2GB/4GB de RAM.
   * Apunta el registro `A` de tu dominio (ej. `turnos.miempresa.cl`) a la IP Pública del VPS.

2. **Asegurar las Variables de Entorno (`.env`)**
   ```env
   DEFAULT_ADMIN_EMAIL="admin@miempresa.cl"
   DEFAULT_ADMIN_PASSWORD="UnPasswordMuySeguro123"
   POSTGRES_PASSWORD="DbPasswordComplejo99"
   
   # ¡CRÍTICO! Restringir los orígenes permitidos
   BACKEND_CORS_ORIGINS=["https://turnos.miempresa.cl"]
   ```

3. **Instalar Traefik o Nginx (Recomendado: Traefik + Let's Encrypt)**
   No debes exponer `8000` directamente a internet. Debes ocultarlo detrás de un servidor proxy que asigne certificados SSL automáticos. 

   Si decides usar **Nginx**, tu configuración básica en `/etc/nginx/sites-available/turnos` debería verse así:
   
   ```nginx
   server {
       server_name turnos.miempresa.cl;

       location / {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           
           # Configuraciones clave para Server-Sent Events (Monitor.html)
           proxy_set_header Connection '';
           proxy_buffering off;
           proxy_cache off;
           chunked_transfer_encoding off;
           proxy_read_timeout 86400s;
           proxy_send_timeout 86400s;
       }
   }
   ```
   *Luego correrías `certbot --nginx -d turnos.miempresa.cl` para habilitar SSL.*

4. **Levantar el Core de la Fila**
   ```bash
   docker-compose up -d
   ```

---

## 📊 Anexo: Encender la Telemetría (Opcional)

Si experimentas problemas de rendimiento y quieres auditar la base de datos o el tráfico en tiempo real, puedes encender la cápsula de monitoreo anexa. Esta incluye Grafana, Prometheus y Sonarqube. 

*(Asegúrate de tener al menos 4GB de RAM libres antes de encender esto)*

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```
* **Grafana:** Disponible en el puerto `:3000` (Conexión a Prometheus ya pre-cableada).
* **Prometheus:** Métricas base en `:9090`.
* **Sonarqube:** Auditoría de Calidad en `:9000`.
