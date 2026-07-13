# Informe de Arquitectura y Seguridad Multicloud - NUAMPY

Este informe presenta la topología, justificación técnica y medidas de seguridad de la infraestructura Multicloud diseñada para el despliegue del software de calificaciones tributarias **NUAMPY**, con base en las credenciales y direccionamiento reales provistos.

---

## 1. Diseño de la Topología Multicloud

La arquitectura de la solución se distribuye de manera híbrida entre **Microsoft Azure** (para cómputo y auditoría) y **Amazon Web Services (AWS)** (para base de datos relacional transaccional).

```mermaid
graph TD
    subgraph Public_Internet ["Internet Pública"]
        Client["Cliente / Corredor"] -->|HTTPS (Puerto 443)| VM_Azure
        Admin["Administrador de Sistemas"] -->|SSH (Puerto 22)| VM_Azure
    end

    subgraph Azure_Cloud ["Nube de Microsoft Azure (Grupo: nuampyGR-Azure)"]
        subgraph VNet_Azure ["Azure Virtual Network (172.16.0.0/16)"]
            VM_Azure["Azure VM: nuampyVM <br>(IP: 20.110.123.149)<br>[Flask App Web]"]
            PrivateLink["Azure Private Link / Endpoint"] --> CosmosDB
        end
        CosmosDB["Azure Cosmos DB: nuampy-logs <br>[API NoSQL Logs]"]
    end

    subgraph AWS_Cloud ["Nube de AWS (Región US-East-1)"]
        subgraph VPC_AWS ["AWS VPC (10.0.0.0/16)"]
            subgraph Private_Subnet ["Subnet Privada Multi-AZ"]
                RDS["AWS RDS: nuampyDB <br>(Endpoint: nuampydb.c7saowikmas3...rds.amazonaws.com)<br>[MySQL 3306]"]
            end
        end
        KMS["AWS KMS (Cifrado de RDS)"] -.-> RDS
    end

    %% Flujos de datos encriptados
    VM_Azure -->|Acceso SQL Encriptado (Puerto 3306)| RDS
    VM_Azure -->|API NoSQL Segura (HTTPS 443)| PrivateLink

    %% Estilos Visuales
    classDef aws fill:#FF9900,stroke:#333,stroke-width:1px,color:#fff;
    classDef azure fill:#0089D6,stroke:#333,stroke-width:1px,color:#fff;
    classDef internet fill:#7F8C8D,stroke:#333,stroke-width:1px,color:#fff;
    class RDS,KMS aws;
    class VM_Azure,CosmosDB,PrivateLink azure;
    class Client,Admin internet;
```

### Flujo de Acciones de la Solución
1. **Acceso Web (Cómputo en Azure VM)**: Los usuarios se conectan por HTTPS (puerto 443) o SSH para administración (puerto 22) a la máquina virtual **nuampyVM** (IP: `20.110.123.149`), donde se hospeda la aplicación Flask.
2. **Acceso de Datos Transaccionales (Base de Datos en AWS RDS)**: Las operaciones CRUD de usuarios, calificaciones y solicitudes se direccionan al motor relacional **nuampyDB** en AWS RDS (puerto 3306) con el usuario `nuampyAWS`. La comunicación se asegura mediante el filtrado de red del grupo de seguridad de RDS, que solo admite conexiones entrantes originadas desde la IP pública de la máquina virtual de Azure (`20.110.123.149`).
3. **Auditoría e Inalterabilidad de Logs (Azure Cosmos DB)**: Las operaciones sensibles se registran y envían de manera síncrona a la base de datos NoSQL **nuampy-logs** de Azure Cosmos DB en el puerto 443, autenticándose a través de su Clave Principal única.

---

## 2. Descripción y Justificación de la Arquitectura Seleccionada

Esta arquitectura multicloud aprovecha las fortalezas operativas específicas de cada nube:

* **Computación y Administración Unificada en Azure**: Hospedar la aplicación web en **Azure VM (nuampyVM)** dentro del mismo grupo de recursos (`nuampyGR-Azure`) que **Cosmos DB** minimiza la latencia para las peticiones de escritura rápida de logs de auditoría.
* **Separación Física de Datos y Auditoría**: Guardar la base de datos transaccional en **AWS RDS (nuampyDB)** y el histórico de logs en **Azure Cosmos DB** previene problemas de alteración de bitácoras de auditoría en caso de que una de las nubes experimente un incidente de seguridad crítico o de control de acceso.
* **Redundancia y Continuidad de Negocio**: Al estar la base de datos en AWS y la aplicación web en Azure, un fallo catastrófico en la infraestructura global de un proveedor no interrumpe el acceso o la preservación de los datos en el otro, garantizando una alta resiliencia operacional.

---

## 3. Descripción Técnica de los Servicios Seleccionados

| Servicio / Componente | Proveedor | Nombre del Recurso | Detalle de Conexión / Parámetros | Justificación |
| :--- | :--- | :--- | :--- | :--- |
| **Máquina Virtual (Cómputo)** | Azure | `nuampyVM` | IP: `20.110.123.149`, Usuario: `nuampyVMuser` | Aloja el servicio Flask Web. Expone puertos 22 (SSH) y 443 (HTTPS). |
| **Base de Datos Relacional** | AWS | `nuampyDB` | Host: `nuampydb.c7saowikmas3.us-east-1.rds.amazonaws.com` | Almacena datos transaccionales con consistencia ACID mediante el motor MySQL. |
| **Base de Datos NoSQL (Logs)** | Azure | `nuampy-logs` | URI: `https://nuampy-logs.documents.azure.com:443/` | Almacena de forma masiva y veloz los logs en formato JSON nativo mediante el SDK NoSQL. |
| **Firewall / Red de Seguridad** | AWS / Azure | Security Groups / IP Firewall | Regla Inbound en AWS RDS: permitir puerto 3306 desde `20.110.123.149/32`. | Previene conexiones externas no autorizadas a los puertos de datos estructurados. |

---

## 4. Ventajas y Beneficios de la Arquitectura Seleccionada

1. **Rendimiento de Logs Óptimo**: Al estar `nuampyVM` y `nuampy-logs` en la red troncal de Microsoft Azure, las escrituras de logs se realizan a latencias insignificantes, sin bloquear el hilo principal de la aplicación.
2. **Independencia en Auditoría**: Cumple con normas ISO 27001 sobre el registro de auditorías en sistemas aislados de los servidores operacionales principales.
3. **Respaldo Dinámico (Fallback)**: El controlador de la aplicación está programado para escribir los logs en MySQL si la red inter-nube hacia Cosmos DB experimenta interrupciones, asegurando continuidad operacional sin pérdida de datos.

---

## 5. Inclusión y Descripción de Aspectos de Seguridad

### A. Estándares y Protocolos Implementados (NIST SP 800-53 / ISO 27001)
* **Control de Acceso Basado en Roles (RBAC)**: El código Flask interactúa con AWS RDS utilizando el usuario restringido `nuampyAWS` con permisos acotados al esquema `nuampyDB`, minimizando el impacto ante un robo de credenciales operacionales.
* **Cifrado en Tránsito**: 
  - Todo el tráfico cliente-servidor transita cifrado por HTTPS.
  - La conexión hacia Azure Cosmos DB utiliza cifrado TLS 1.3 forzado mediante puerto 443.
  - Las transacciones SQL hacia RDS utilizan conexiones TCP cifradas con SSL.
* **Cifrado en Reposo**: RDS de AWS y Cosmos DB de Azure implementan por defecto cifrado transparente de almacenamiento con algoritmos simétricos AES-256.

### B. Aspectos de Seguridad de Aplicación (OWASP Top 10)
* **Protección contra Inyecciones SQL**: Implementado en el módulo [dataBase.py](file:///c:/Users/rooki/OneDrive/NUAMPY/data/dataBase.py) mediante sentencias parametrizadas y blindaje de inputs.
* **Hashing de Contraseñas**: SHA-256 aplicado antes de almacenar o comparar registros en la tabla de `usuarios`.
* **Protección contra CSRF**: Tokenización criptográfica en formularios HTML.

---

## 6. Perspectivas de Funcionalidad: Administrador y Cliente

La solución diferencia claramente los roles de acceso para cumplir con políticas de control y auditoría:

* **Perspectiva del Cliente (Corredor / Invitado)**:
  - **Funcionalidades**: Visualización del dashboard de calificaciones tributarias, filtrado dinámico por mercado (Chile, Perú, Colombia), ingreso manual de calificaciones mediante factores o montos, carga masiva de archivos CSV y generación de solicitudes de eliminación para sus propios registros.
  - **Seguridad**: Sus acciones están limitadas a su propio contexto operacional. No pueden visualizar los logs globales ni gestionar usuarios.
* **Perspectiva del Administrador de Sistemas**:
  - **Funcionalidades**: Gestión total del ciclo de vida de usuarios (creación, modificación y eliminación de credenciales), aprobación o rechazo de solicitudes de eliminación de calificaciones y visualización en tiempo real del registro de logs de auditoría (`/logs`).
  - **Seguridad**: Cuenta con privilegios administrativos elevados sobre la aplicación Flask y requiere un canal SSH directo cifrado (puerto 22) para el mantenimiento del servidor de computación.

---

## 7. Procedimientos de Seguridad en la Infraestructura (Criterio 3.1.4)

Para garantizar un entorno seguro y estandarizado, se implementan los siguientes procedimientos operativos estándar (SOP):

### Procedimiento 1: Gestión de Identidades y Rotación de Credenciales (ISO 27001 A.9.2)
1. Las contraseñas de las cuentas de base de datos (`nuampyAWS`) y de administración del servidor virtual (`nuampyVMuser`) deben tener una longitud mínima de 14 caracteres, incluyendo letras mayúsculas, minúsculas, números y caracteres especiales.
2. Se programa una rotación obligatoria de la clave principal de Azure Cosmos DB y la credencial de AWS RDS cada 90 días mediante scripts automatizados en Azure CLI y AWS CLI.
3. Las sesiones web expiran automáticamente tras 15 minutos de inactividad para prevenir secuestros de sesión en equipos compartidos.

### Procedimiento 2: Parcheo y Actualización de la Infraestructura (ISO 27001 A.12.6)
1. Monitoreo semanal de boletines de vulnerabilidades de seguridad para el sistema operativo Linux de la máquina virtual `nuampyVM` y las dependencias de Python (Flask, PyMySQL, Azure-Cosmos).
2. Aplicación de parches de seguridad críticos en una ventana de mantenimiento mensual, previa validación en un ambiente de desarrollo local idéntico.

### Procedimiento 3: Respaldo y Recuperación ante Desastres (NIST SP 800-53 CP-9)
1. AWS RDS MySQL tiene activada la retención de respaldos automatizados durante 14 días.
2. Se programa un respaldo completo semanal exportado hacia un contenedor de Azure Blob Storage o bucket S3 inmutable, asegurando redundancia de almacenamiento fuera de la base de datos de producción.

---

## 8. Evaluación del Desempeño de Seguridad (Criterio 3.1.3)

La efectividad de las medidas de seguridad multicloud se mide y evalúa sistemáticamente mediante los siguientes mecanismos:

1. **Auditoría Sistemática mediante Logs en Azure Cosmos DB**:
   - Cada evento crítico (logins fallidos, cambios de rol, inserción/eliminación de calificaciones) genera un registro inalterable.
   - Se evalúa mensualmente la tasa de intentos fallidos de login para detectar posibles ataques de fuerza bruta dirigidos a la IP pública `20.110.123.149`.
2. **Escaneo de Vulnerabilidades y Cumplimiento (Microsoft Defender for Cloud)**:
   - Se utiliza el servicio nativo de Microsoft Azure para evaluar en tiempo real la postura de seguridad de la máquina virtual `nuampyVM` contra los estándares CIS Benchmarks y PCI-DSS.
3. **Control de Tránsito y Firewall en AWS**:
   - Revisión periódica de los logs de flujo de VPC (VPC Flow Logs) en AWS para auditar que solo la IP `20.110.123.149` de Azure haya interactuado exitosamente con el puerto 3306 de RDS, descartando intentos de conexión externa bloqueados de forma pasiva por los Security Groups.
