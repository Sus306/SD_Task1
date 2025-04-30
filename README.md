# SD_Task1
# Scalable Insult Filter

Este proyecto implementa un sistema escalable de gestión y filtrado de insultos utilizando cuatro middleware de comunicación diferentes:

- **XML-RPC**
- **PyRO**
- **Redis**
- **RabbitMQ**

## Estructura del Proyecto
```
/scalable_insult_filter
    ├── insult_service/
    │   ├── insult_service_xmlrpc.py
    │   ├── insult_service_pyro.py
    │   ├── insult_service_redis.py
    │   ├── insult_service_rabbitmq.py
    ├── insult_filter/
    │   ├── insult_filter_xmlrpc.py
    │   ├── insult_filter_pyro.py
    │   ├── insult_filter_redis.py
    │   ├── insult_filter_rabbitmq.py
    ├── script.py  # Guion de ejecución
    ├── README.md  # Instrucciones
```

## Instalación de Dependencias
Antes de ejecutar el proyecto, asegúrate de tener instaladas las siguientes bibliotecas:

```bash
pip install pyyaml redis pika Pyro4
```

Además, instala y ejecuta Redis y RabbitMQ:

```bash
# Instalación de Redis (Ubuntu/Debian)
sudo apt install redis-server
redis-server

# Instalación de RabbitMQ (Ubuntu/Debian)
sudo apt install rabbitmq-server
sudo rabbitmq-server

# Instalación de Pyro4 (Ubuntu/Debian)
sudo pip install Pyro4
pyro4-ns
```

## Ejecución del Proyecto
Para ejecutar los servicios simultáneamente, ejecuta:

```bash
python3 framework.py
```

Este comando iniciará los servidores de **XML-RPC, PyRO, Redis y RabbitMQ** en segundo plano.

## Pruebas y Uso
Puedes interactuar con los servicios de las siguientes maneras:

### **XML-RPC**
- Usa un cliente XML-RPC para llamar a los métodos `add_insult(insult)` y `get_insults()`.

### **PyRO**
- Utiliza `Pyro4.Proxy(uri)` para conectarte al servidor y probar los métodos expuestos.

### **Redis**
- Usa `redis-cli` o código Python para agregar y recuperar insultos desde la base de datos.

### **RabbitMQ**
- Publica mensajes en la cola `insults` y observa su recepción en la consola.

## Análisis de Rendimiento
Para evaluar el rendimiento de cada solución:
1. **Prueba en un solo nodo**: Ejecuta `script.py` y somete cada servicio a una carga alta para medir la cantidad de solicitudes procesadas.
2. **Prueba en múltiples nodos**: Configura el código para ejecutarse en varias máquinas y mide la escalabilidad.
3. **Escalado dinámico**: Implementa una estrategia de ajuste dinámico de nodos basado en la carga de trabajo.

## Documentación y Entrega
Sube el código a un repositorio de GitHub e incluye en Moodle:
- Un PDF con el enlace al repositorio.
- Documentación detallada del diseño y pruebas realizadas.
- Gráficos comparativos de rendimiento.

## Contacto
Para cualquier duda, contacta con el equipo de desarrollo.


## TESTS
Ejecutar: pytest tests 


