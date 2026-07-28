# Despliegue en AWS - Demo (EC2 Free Tier)

Guia para desplegar **image-tools** en AWS usando EC2 t2.micro + Docker + SAM CLI.

## Arquitectura

```
┌─────────────┐      ┌──────────────────────────────┐
│   Cliente   │─────>│  EC2 t2.micro (Free Tier)    │
│  (browser)  │:8070 │  ┌────────────────────────┐  │
└─────────────┘      │  │  Docker                │  │
                     │  │  ┌──────────────────┐  │  │
                     │  │  │ image-tools:8070 │  │  │
                     │  │  │ Gunicorn 1 worker│  │  │
                     │  │  │ + u2net model    │  │  │
                     │  │  └──────────────────┘  │  │
                     │  └────────────────────────┘  │
                     └──────────────────────────────┘
```

- **EC2 t2.micro**: 1 vCPU, 1 GB RAM, 750 hrs/mes gratis (12 meses)
- **Docker**: Corre el contenedor con la app + modelo
- **SAM/CloudFormation**: Infraestructura como codigo (Security Group, IAM, EC2)

## Prerequisitos

1. **AWS CLI** configurado con credenciales:
   ```powershell
   aws configure
   # Access Key ID, Secret Access Key, Region: us-east-1, Output: json
   ```

2. **SAM CLI**:
   ```powershell
   winget install Amazon.SAM-CLI
   ```

3. **Docker Desktop** corriendo localmente

4. **Key Pair de EC2** (para SSH):
   - Ve a AWS Console > EC2 > Key Pairs > Create Key Pair
   - Nombre: `image-tools-key` (o el que prefieras)
   - Tipo: RSA, formato .pem
   - Descarga el .pem y guardalo en `~\.ssh\image-tools-key.pem`

5. Verificar todo:
   ```powershell
   aws sts get-caller-identity   # debe mostrar tu Account ID
   sam --version                  # v1.x
   docker --version               # Docker Engine
   Test-Path ~\.ssh\image-tools-key.pem  # True
   ```

## Deploy rapido (un solo comando)

```powershell
.\scripts\deploy.ps1 -KeyPairName "image-tools-key"
```

Esto automaticamente:
1. Valida que tengas AWS CLI, SAM, Docker, SSH
2. Genera un token de API aleatorio (o usa `-ApiToken "tu-token"`)
3. Despliega la infra con SAM (EC2 + Security Group + IAM)
4. Espera a que la instancia este lista
5. Construye la imagen Docker localmente
6. Transfiere la imagen a EC2 via SCP
7. Arranca el contenedor en la instancia

### Opciones del script

```powershell
# Con token personalizado
.\scripts\deploy.ps1 -KeyPairName "image-tools-key" -ApiToken "mi-token-seguro"

# Key pair en otra ubicacion
.\scripts\deploy.ps1 -KeyPairName "my-key" -KeyPairPath "C:\keys\my-key.pem"

# Otra region
.\scripts\deploy.ps1 -KeyPairName "my-key" -Region "us-west-2"

# Saltar build Docker (si ya lo construiste antes)
.\scripts\deploy.ps1 -KeyPairName "my-key" -SkipBuild
```

## Deploy manual (paso a paso)

### 1. Desplegar infraestructura

```powershell
sam deploy `
    --template-file template.yaml `
    --stack-name image-tools-demo `
    --region us-east-1 `
    --capabilities CAPABILITY_NAMED_IAM `
    --parameter-overrides "Environment=production ApiTokens=tu-token-seguro MaxUploadMB=10 LogLevel=INFO KeyPairName=image-tools-key" `
    --no-confirm-changeset
```

### 2. Obtener IP de la instancia

```powershell
$IP = aws cloudformation describe-stacks --stack-name image-tools-demo --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" --output text
echo $IP
```

### 3. Build y transferir imagen

```powershell
# Build local
docker build -t image-tools:latest .

# Exportar a tar
docker save image-tools:latest -o image-tools.tar

# Transferir a EC2
scp -i ~\.ssh\image-tools-key.pem image-tools.tar ec2-user@${IP}:/tmp/
```

### 4. Arrancar contenedor en EC2

```powershell
ssh -i ~\.ssh\image-tools-key.pem ec2-user@$IP

# Ya en la instancia:
sudo docker load -i /tmp/image-tools.tar
sudo docker run -d --name image-tools `
    --env-file /opt/image-tools/.env `
    -e PORT=8070 -e ENVIRONMENT=production -e NUMBA_DISABLE_JIT=1 `
    -p 8070:8070 --memory=900m --restart unless-stopped `
    image-tools:latest
```

### 5. Verificar

```powershell
curl http://${IP}:8070/
```

## Verificar el deploy

```powershell
# Health check (sin autenticacion)
curl http://<IP>:8070/

# Swagger UI (sin autenticacion)
# Abrir en browser: http://<IP>:8070/docs

# Endpoint con autenticacion
curl -H "X-API-KEY: tu-token" http://<IP>:8070/tools/api/v1/image/process
```

## SSH a la instancia

```powershell
ssh -i ~\.ssh\image-tools-key.pem ec2-user@<IP>

# Ver logs del contenedor
sudo docker logs image-tools

# Ver estado
sudo docker ps

# Reiniciar
sudo docker restart image-tools
```

## Cleanup (eliminar todo)

Cuando termines el demo, elimina todos los recursos para evitar costos:

```powershell
.\scripts\teardown.ps1
```

Esto elimina: EC2 instance, Security Group, IAM roles, y el stack de CloudFormation.
El Key Pair permanece en tu cuenta (no genera costo).

## Costos Free Tier (12 primeros meses)

| Servicio | Free Tier | Nota |
|----------|-----------|------|
| EC2 t2.micro | 750 hrs/mes gratis | ~31 dias 24/7 |
| EBS 20 GB gp3 | 30 GB gratis | Cubierto |
| Data Transfer | 100 GB/mes salida | Mas que suficiente |
| CloudWatch | 5 GB logs | Basico incluido |

**Costo total del demo: $0** (dentro de Free Tier)

## Limitaciones del t2.micro para este proyecto

- 1 GB RAM: el modelo u2net usa ~500 MB, queda justo
- 1 worker de Gunicorn: procesa una imagen a la vez
- Primer request tarda ~90s (carga del modelo)
- Imagenes grandes (>5 MB) pueden ser lentas

Para produccion real, considerar t3.small (2 GB RAM, ~$15/mes).

## Troubleshooting

### La instancia no responde en el puerto 8070
```powershell
# Verificar Security Group
aws ec2 describe-security-groups --filters "Name=group-name,Values=image-tools-sg" --query "SecurityGroups[0].IpPermissions"

# SSH y verificar Docker
ssh -i ~\.ssh\image-tools-key.pem ec2-user@<IP>
sudo docker ps
sudo docker logs image-tools
```

### Error "Connection refused" en SSH
- El Security Group permite SSH solo desde el CIDR configurado
- Por defecto es 0.0.0.0/0 (cualquier IP)
- Verifica que tu IP no este bloqueada por otro security group

### El contenedor se reinicia constantemente (OOM)
```powershell
# Ver si murio por memoria
sudo docker inspect image-tools | grep -i oom

# Solucion: usar swap
sudo dd if=/dev/zero of=/swapfile bs=128M count=8
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### El modelo tarda mucho en cargar
Es normal en t2.micro (~60-90s). El health check esta configurado con tolerancia alta.
Despues del primer request, los siguientes son rapidos (~2-5s).

### Error en user-data (Docker no se instalo)
```powershell
# Ver log de user-data
ssh -i ~\.ssh\image-tools-key.pem ec2-user@<IP>
cat /var/log/user-data.log
```
